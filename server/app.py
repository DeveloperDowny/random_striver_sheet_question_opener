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

from db_config import DBConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler("api_debug.log", mode="a"), logging.StreamHandler()],
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
