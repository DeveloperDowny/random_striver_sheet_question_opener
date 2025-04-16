# -*- coding: utf-8 -*-
"""
FastAPI wrapper for the SheetHandler application.
Provides REST API endpoints to interact with the sheet processing functionality.
"""

import logging
import random
import time
from typing import List, Optional, Dict, Any
import os

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Import your existing components
from sheet_handler_factory import SheetHandlerFactory
from sheet_handler import SheetHandler
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


# Create FastAPI app
app = FastAPI(
    title="SheetHandler API",
    description="API for accessing and managing study sheets from MongoDB",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database dependency
def get_db_config():
    """Get database configuration."""
    return DBConfig(_env_file=os.getenv("ENV_FILE_PATH", ".env"))


def get_mongo_client(db_config: DBConfig = Depends(get_db_config)):
    """Get MongoDB client as a dependency."""
    try:
        client = MongoClient(db_config.MONGODB_URI)
        # Validate connection
        client.admin.command("ismaster")
        logger.info(f"Connected to MongoDB using {db_config.DATABASE_NAME}")
        yield client
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
    finally:
        client.close()
        logger.info("MongoDB connection closed")


# Available sheet types
SHEET_TYPES = [
    "sde_sheet",
    "dbms_core_sheet",
    "os_core_sheet",
    "cn_core_sheet",
    "lc_sql_50",
    "must_do_product_gfg",
    "lc_dsa_75",
    "microsoft_dsa",
    "phonepe_dsa",
    "oracle_dsa",
    "linux_commands",
    "docker_commands",
    "langgraph",
    "dsa_common_patterns",
]


@app.get("/", response_model=StatusResponse)
async def root():
    """Root endpoint providing API status."""
    return StatusResponse(
        status="success",
        message="SheetHandler API is running. Use /docs for API documentation.",
    )


@app.get("/sheet-types", response_model=SheetTypeResponse)
async def get_sheet_types():
    """Get all available sheet types."""
    return SheetTypeResponse(sheet_types=SHEET_TYPES)


@app.post("/filter-sheets", response_model=SheetTypeResponse)
async def filter_sheets(request: SheetSelectionRequest):
    """Filter sheet types based on request criteria."""
    filtered_sheets = SHEET_TYPES.copy()

    # Apply filter if provided
    if request.filter_text:
        filtered_sheets = [
            sheet
            for sheet in SHEET_TYPES
            if request.filter_text.lower() in sheet.lower()
        ]

    # Return empty list if no matches
    if not filtered_sheets:
        logger.warning(f"No sheet types found with filter: {request.filter_text}")
        return SheetTypeResponse(sheet_types=[])

    return SheetTypeResponse(sheet_types=filtered_sheets)


@app.post("/select-topic", response_model=TopicResponse)
async def select_topic(
    request: SheetSelectionRequest,
    mongo_client: MongoClient = Depends(get_mongo_client),
    db_config: DBConfig = Depends(get_db_config),
):
    """Select a topic from sheets based on request criteria."""
    try:
        # Filter sheets first
        filtered_sheets = SHEET_TYPES.copy()
        if request.filter_text:
            filtered_sheets = [
                sheet
                for sheet in SHEET_TYPES
                if request.filter_text.lower() in sheet.lower()
            ]

        if not filtered_sheets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching sheet types found",
            )

        # Select sheet type based on request
        sheet_type = None
        if request.random_selection:
            sheet_type = random.choice(filtered_sheets)
        elif request.selected_index is not None:
            if 0 <= request.selected_index < len(filtered_sheets):
                sheet_type = filtered_sheets[request.selected_index]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Index {request.selected_index} out of range for {len(filtered_sheets)} sheets",
                )
        else:
            # Default to first sheet if neither random nor index specified
            sheet_type = filtered_sheets[0]

        logger.info(f"Selected sheet type: {sheet_type}")

        # Create handler and process
        handler = SheetHandlerFactory.create_handler(
            sheet_type=sheet_type,
            mongo_client=mongo_client,
            db_name=db_config.DATABASE_NAME,
        )

        # Modified process method that returns data instead of logging and printing
        # We need to extract results from handler.process()
        history = handler._read_history()

        # Get data from MongoDB
        sheet_data = list(
            mongo_client[db_config.DATABASE_NAME][handler.file_name].find({})
        )
        if not sheet_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for sheet type: {sheet_type}",
            )

        # Filter out solved items
        filtered_data = handler.remove_solved(sheet_data, history)
        if not filtered_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No unsolved topics found in {sheet_type}",
            )

        # Select random topic
        random_topic = handler.get_random_topic(filtered_data)
        if not random_topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to select a random topic",
            )

        # Get information from topic
        topic_id = str(random_topic.get("id", "unknown"))
        title = handler.get_title(random_topic)
        link = handler.create_link(title)

        # Update history
        handler.update_history(history, topic_id)


        from bson.json_util import dumps
        import json
        
        # Return response
        return TopicResponse(
            sheet_type=sheet_type,
            topic_id=topic_id,
            title=title,
            link=link,
            details=json.loads(dumps(random_topic)),
        )

    except ValueError as e:
        logger.error(f"Value error in select_topic: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error in select_topic: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while selecting topic",
        )


@app.post("/mark-revision", response_model=StatusResponse)
async def mark_revision(
    request: RevisionRequest,
    mongo_client: MongoClient = Depends(get_mongo_client),
    db_config: DBConfig = Depends(get_db_config),
):
    """Mark a topic for revision and remove it from history."""
    try:
        # Create the appropriate handler
        handler = SheetHandlerFactory.create_handler(
            sheet_type=request.sheet_type,
            mongo_client=mongo_client,
            db_name=db_config.DATABASE_NAME,
        )

        # Mark for revision
        handler.mark_revision(request.topic_id)

        return StatusResponse(
            status="success", message=f"Topic {request.topic_id} marked for revision"
        )
    except ValueError as e:
        logger.error(f"Value error in mark_revision: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error in mark_revision: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while marking for revision",
        )


@app.get("/revision-list/{sheet_type}", response_model=Dict[str, List[str]])
async def get_revision_list(
    sheet_type: str,
    mongo_client: MongoClient = Depends(get_mongo_client),
    db_config: DBConfig = Depends(get_db_config),
):
    """Get list of topics marked for revision for a specific sheet type."""
    try:
        if sheet_type not in SHEET_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sheet type: {sheet_type}",
            )

        db = mongo_client[db_config.DATABASE_NAME]
        revision_collection = db["revision"]

        revision_doc = revision_collection.find_one({"sheet_name": sheet_type})
        if not revision_doc or "revision_ids" not in revision_doc:
            return {"revision_ids": []}

        return {"revision_ids": revision_doc["revision_ids"]}
    except Exception as e:
        logger.exception(f"Error getting revision list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching revision list",
        )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
