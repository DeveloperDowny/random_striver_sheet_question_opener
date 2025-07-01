# -*- coding: utf-8 -*-
"""
FastAPI wrapper for the SheetHandler application.
Provides REST API endpoints to interact with the sheet processing functionality.
"""

import json
import logging
import random
from typing import Dict, List

from bson.json_util import dumps
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

from db_config import DBConfig
from schemas import (
    EnrichedTopicResponse,
    RevisionRequest,
    SheetSelectionRequest,
    SheetTypeResponse,
    StatusResponse,
    TopicResponse,
    TopicEnrichmentRequest,
    SearchResult,
)
from tavily_search_service import TavilySearchService
from utils import (
    get_mongo_client,
    get_db_config,
    get_tavily_service,
    categorize_search_results,
    generate_related_topics,
    extract_key_concepts,
)

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="SheetHandler API",
    description="API for accessing and managing study sheets from MongoDB",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=StatusResponse)
async def root():
    return StatusResponse(
        status="success",
        message="SheetHandler API is running. Use /docs for API documentation.",
    )


@app.get("/sheet-types", response_model=SheetTypeResponse)
async def get_sheet_types(
    mongo_client: MongoClient = Depends(get_mongo_client),
    db_config: DBConfig = Depends(get_db_config),
):
    topics_col = mongo_client[db_config.DATABASE_NAME]["topics"]
    sheet_names = topics_col.distinct("sheet_name")
    return SheetTypeResponse(sheet_types=sheet_names)


@app.post("/filter-sheets", response_model=SheetTypeResponse)
async def filter_sheets(
    request: SheetSelectionRequest,
    mongo_client: MongoClient = Depends(get_mongo_client),
    db_config: DBConfig = Depends(get_db_config),
):
    topics_col = mongo_client[db_config.DATABASE_NAME]["topics"]
    all_sheets = topics_col.distinct("sheet_name")
    if request.filter_text:
        filtered = [s for s in all_sheets if request.filter_text.lower() in s.lower()]
    else:
        filtered = all_sheets
    return SheetTypeResponse(sheet_types=filtered)


def _read_history(mongo_client, db_config):
    history_col = mongo_client[db_config.DATABASE_NAME]["history"]
    history_docs = list(history_col.find({}, {"_id": 0, "topic_id": 1}))
    return set(doc["topic_id"] for doc in history_docs)


def update_history(mongo_client, db_config, topic_id):
    history_col = mongo_client[db_config.DATABASE_NAME]["history"]
    if not history_col.find_one({"topic_id": topic_id}):
        history_col.insert_one({"topic_id": topic_id})


def remove_solved(topics: List[Dict], history_ids: set):
    return [t for t in topics if str(t.get("id")) not in history_ids]


def get_random_topic(topics: List[Dict]):
    return random.choice(topics) if topics else None


def get_title(topic: Dict):
    return topic.get("title") or topic.get("name") or "Untitled Topic"


def create_link(title: str):
    return f"https://www.google.com/search?q={'+'.join(title.split())}"


def mark_topic_for_revision(mongo_client, db_config, sheet_type: str, topic_id: str):
    revision_col = mongo_client[db_config.DATABASE_NAME]["revision"]
    revision_col.update_one(
        {"sheet_name": sheet_type},
        {"$addToSet": {"revision_ids": topic_id}},
        upsert=True,
    )
    # Also remove from history if it exists
    history_col = mongo_client[db_config.DATABASE_NAME]["history"]
    history_col.delete_one({"topic_id": topic_id})


@app.post("/select-topic", response_model=TopicResponse)
async def select_topic(
    request: SheetSelectionRequest,
    mongo_client: MongoClient = Depends(get_mongo_client),
    db_config: DBConfig = Depends(get_db_config),
):
    topics_col = mongo_client[db_config.DATABASE_NAME]["topics"]
    sheet_names = topics_col.distinct("sheet_name")

    if request.filter_text:
        sheet_names = [
            s for s in sheet_names if request.filter_text.lower() in s.lower()
        ]

    if not sheet_names:
        raise HTTPException(status_code=404, detail="No matching sheets")

    if request.random_selection:
        selected_sheet = random.choice(sheet_names)
    elif request.selected_index is not None:
        if 0 <= request.selected_index < len(sheet_names):
            selected_sheet = sheet_names[request.selected_index]
        else:
            raise HTTPException(status_code=400, detail="Invalid index")
    else:
        selected_sheet = sheet_names[0]

    history = _read_history(mongo_client, db_config)
    all_topics = list(topics_col.find({"sheet_name": selected_sheet}))
    filtered = remove_solved(all_topics, history)
    if not filtered:
        raise HTTPException(status_code=404, detail="No unsolved topics")

    topic = get_random_topic(filtered)
    if not topic:
        raise HTTPException(status_code=500, detail="Failed to pick topic")

    topic_id = str(topic.get("id", "unknown"))
    title = get_title(topic)
    link = topic.get("link", None) or create_link(title)

    update_history(mongo_client, db_config, topic_id)

    return TopicResponse(
        sheet_type=selected_sheet,
        topic_id=topic_id,
        title=title,
        link=link,
        details=json.loads(dumps(topic)),
    )


@app.post("/mark-revision", response_model=StatusResponse)
async def mark_revision(
    request: RevisionRequest,
    mongo_client: MongoClient = Depends(get_mongo_client),
    db_config: DBConfig = Depends(get_db_config),
):
    mark_topic_for_revision(
        mongo_client, db_config, request.sheet_type, request.topic_id
    )
    return StatusResponse(status="success", message="Marked for revision")


@app.get("/revision-list/{sheet_type}", response_model=Dict[str, List[str]])
async def get_revision_list(
    sheet_type: str,
    mongo_client: MongoClient = Depends(get_mongo_client),
    db_config: DBConfig = Depends(get_db_config),
):
    revision_col = mongo_client[db_config.DATABASE_NAME]["revision"]
    doc = revision_col.find_one({"sheet_name": sheet_type})
    return {"revision_ids": doc.get("revision_ids", []) if doc else []}


@app.post("/enrich-topic", response_model=EnrichedTopicResponse)
async def enrich_topic(
    request: TopicEnrichmentRequest,
    tavily_service: TavilySearchService = Depends(get_tavily_service),
):
    """
    Enrich a topic with web search results and additional information
    """
    try:
        # Construct search query
        search_query = request.title
        if request.sheet_type:
            search_query = search_query + " " + " ".join(request.sheet_type.split("_"))
        if request.description:
            search_query += f" {request.description}"
        if request.additional_context:
            search_query += f" {request.additional_context}"

        logger.info(f"Enriching topic with search query: {search_query}")

        # Perform web search
        search_response = await tavily_service.search(search_query, max_results=8)

        # Extract search results
        raw_results = search_response.get("results", [])

        # Convert to SearchResult objects
        search_results = []
        for result in raw_results:
            search_results.append(
                SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    snippet=result.get("content", "")[:300] + "..."
                    if len(result.get("content", "")) > 300
                    else result.get("content", ""),
                )
            )

        # Generate summary from search results
        answer = search_response.get("answer", "")
        if not answer:
            # Fallback summary from first few results
            summary_parts = []
            for result in raw_results[:3]:
                content = result.get("content", "")
                if content:
                    summary_parts.append(content[:100])
            answer = " ".join(summary_parts) + "..."

        # Extract key concepts
        key_concepts = extract_key_concepts(raw_results, request.title)

        # Generate related topics
        related_topics = generate_related_topics(raw_results, request.title)

        # Categorize study resources
        study_resources = categorize_search_results(raw_results)

        return EnrichedTopicResponse(
            original_topic=request,
            search_query=search_query,
            search_results=search_results,
            summary=answer,
            key_concepts=key_concepts,
            related_topics=related_topics,
            study_resources=study_resources,
        )

    except Exception as e:
        logger.error(f"Error enriching topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to enrich topic: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
