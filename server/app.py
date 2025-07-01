# -*- coding: utf-8 -*-
"""
FastAPI wrapper for the SheetHandler application.
Provides REST API endpoints to interact with the sheet processing functionality.
"""

import logging
import random
import os
import json
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.json_util import dumps
import httpx
from db_config import DBConfig
from dotenv import load_dotenv
load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S", 
)
logger = logging.getLogger(__name__)


# Define API models
class SheetTypeResponse(BaseModel):
    sheet_types: List[str] = Field(..., description="List of available sheet types")


class SheetSelectionRequest(BaseModel):
    filter_text: Optional[str] = Field(None, description="Text to filter sheet types")
    selected_index: Optional[int] = Field(None, description="Index of selected sheet")
    random_selection: bool = Field(
        False, description="Whether to select a random sheet"
    )


class TopicResponse(BaseModel):
    sheet_type: str = Field(..., description="Type of sheet processed")
    topic_id: str = Field(..., description="ID of the selected topic")
    title: str = Field(..., description="Title of the selected topic")
    link: str = Field(..., description="Search link for the topic")
    details: Dict[str, Any] = Field(..., description="Additional topic details")


class RevisionRequest(BaseModel):
    sheet_type: str = Field(..., description="Type of sheet")
    topic_id: str = Field(..., description="ID of the topic to mark for revision")


class StatusResponse(BaseModel):
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Additional information")


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


def get_mongo_client():
    db_config = DBConfig(_env_file=os.getenv("ENV_FILE_PATH", ".env"))
    try:
        client = MongoClient(db_config.MONGODB_URI)
        client.admin.command("ismaster")
        logger.info(f"Connected to MongoDB using {db_config.DATABASE_NAME}")
        return client
    except ConnectionFailure:
        raise HTTPException(status_code=503, detail="Database connection failed")


def get_db_config():
    return DBConfig(_env_file=os.getenv("ENV_FILE_PATH", ".env"))


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


# Tavily API configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_BASE_URL = "https://api.tavily.com"



class TopicEnrichmentRequest(BaseModel):
    title: str = Field(..., description="Title of the topic to enrich")
    description: Optional[str] = Field(None, description="Optional description of the topic")
    sheet_type: Optional[str] = Field(None, description="Type of sheet this topic belongs to")
    additional_context: Optional[str] = Field(None, description="Additional context for search")


class SearchResult(BaseModel):
    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    snippet: str = Field(..., description="Snippet/description of the search result")


class EnrichedTopicResponse(BaseModel):
    original_topic: TopicEnrichmentRequest = Field(..., description="Original topic data")
    search_query: str = Field(..., description="Query used for web search")
    search_results: List[SearchResult] = Field(..., description="Web search results")
    summary: str = Field(..., description="AI-generated summary of the topic")
    key_concepts: List[str] = Field(..., description="Key concepts extracted from search")
    related_topics: List[str] = Field(..., description="Related topics for further study")
    study_resources: List[SearchResult] = Field(..., description="Educational resources found")


class TavilySearchService:
    """Service for interacting with Tavily search API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = TAVILY_BASE_URL
        
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Perform web search using Tavily API"""
        if not self.api_key:
            raise HTTPException(
                status_code=500, 
                detail="Tavily API key not configured"
            )
            
        headers = {
            "Content-Type": "application/json",
        }
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": False,
            "max_results": max_results,
            "include_domains": [],
            "exclude_domains": []
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"Tavily API error: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Search service error: {response.status_code}"
                    )
                    
                return response.json()
                
        except httpx.TimeoutException:
            logger.error("Tavily API timeout")
            raise HTTPException(status_code=504, detail="Search service timeout")
        except Exception as e:
            logger.error(f"Tavily API error: {str(e)}")
            raise HTTPException(status_code=500, detail="Search service unavailable")


def get_tavily_service():
    """Dependency to get Tavily search service"""
    return TavilySearchService(TAVILY_API_KEY)

def extract_key_concepts(search_results: List[Dict], topic_title: str) -> List[str]:
    """Extract key concepts from search results"""
    concepts = set()
    
    # Add the main topic
    concepts.add(topic_title)
    
    # Extract from search results
    for result in search_results:
        snippet = result.get("content", "").lower()
        title = result.get("title", "").lower()
        
        # Simple keyword extraction (can be enhanced with NLP)
        import re
        words = re.findall(r'\b[a-zA-Z]{4,}\b', snippet + " " + title)
        
        # Filter for potentially important terms
        important_words = [
            word.title() for word in words 
            if len(word) > 4 and word not in [
                'that', 'this', 'with', 'from', 'they', 'have', 'been', 
                'will', 'more', 'about', 'other', 'which', 'their', 'would'
            ]
        ]
        
        concepts.update(important_words[:3])  # Limit concepts per result
    
    return list(concepts)[:10]  # Return top 10 concepts


def generate_related_topics(search_results: List[Dict], original_topic: str) -> List[str]:
    """Generate related topics from search results"""
    related = set()
    
    for result in search_results:
        title = result.get("title", "")
        
        # Extract potential topics from titles
        if title and title.lower() != original_topic.lower():
            # Clean and format the title
            clean_title = title.replace(original_topic, "").strip()
            if len(clean_title) > 10 and len(clean_title) < 100:
                related.add(clean_title)
    
    return list(related)[:5]  # Return top 5 related topics




def categorize_search_results(search_results: List[Dict]) -> List[SearchResult]:
    """Filter and categorize search results for educational resources"""
    educational_domains = [
        'wikipedia.org', 'edu', 'coursera.org', 'edx.org', 'khanacademy.org',
        'britannica.com', 'nationalgeographic.com', 'scientificamerican.com'
    ]
    
    study_resources = []
    
    for result in search_results:
        url = result.get("url", "")
        title = result.get("title", "")
        content = result.get("content", "")
        
        # Check if it's from an educational domain
        is_educational = any(domain in url.lower() for domain in educational_domains)
        
        # Check if title suggests educational content
        educational_keywords = ['tutorial', 'guide', 'course', 'lesson', 'learn', 'study']
        has_educational_keywords = any(keyword in title.lower() for keyword in educational_keywords)
        
        if is_educational or has_educational_keywords:
            study_resources.append(SearchResult(
                title=title,
                url=url,
                snippet=content[:200] + "..." if len(content) > 200 else content
            ))
    
    return study_resources[:5]  # Return top 5 educational resources

@app.post("/enrich-topic", response_model=EnrichedTopicResponse)
async def enrich_topic(
    request: TopicEnrichmentRequest,
    tavily_service: TavilySearchService = Depends(get_tavily_service)
):
    """
    Enrich a topic with web search results and additional information
    """
    try:
        # Construct search query
        search_query = request.title
        if request.description:
            search_query += f" {request.description}"
        if request.additional_context:
            search_query += f" {request.additional_context}"
        
        # Add educational context to improve results
        search_query += " tutorial guide explanation"
        
        logger.info(f"Enriching topic with search query: {search_query}")
        
        # Perform web search
        search_response = await tavily_service.search(search_query, max_results=8)
        
        # Extract search results
        raw_results = search_response.get("results", [])
        
        # Convert to SearchResult objects
        search_results = []
        for result in raw_results:
            search_results.append(SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                snippet=result.get("content", "")[:300] + "..." if len(result.get("content", "")) > 300 else result.get("content", "")
            ))
        
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
            study_resources=study_resources
        )
        
    except Exception as e:
        logger.error(f"Error enriching topic: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enrich topic: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
