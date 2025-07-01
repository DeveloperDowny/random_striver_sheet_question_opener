# Define API models
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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

    class SearchResult(BaseModel):
        title: str = Field(..., description="Title of the search result")
        url: str = Field(..., description="URL of the search result")
        snippet: str = Field(..., description="Snippet/description of the search result")


class TopicEnrichmentRequest(BaseModel):
    title: str = Field(..., description="Title of the topic to enrich")
    description: Optional[str] = Field(
        None, description="Optional description of the topic"
    )
    sheet_type: Optional[str] = Field(
        None, description="Type of sheet this topic belongs to"
    )
    additional_context: Optional[str] = Field(
        None, description="Additional context for search"
    )


class SearchResult(BaseModel):
    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    snippet: str = Field(..., description="Snippet/description of the search result")


class EnrichedTopicResponse(BaseModel):
    original_topic: TopicEnrichmentRequest = Field(
        ..., description="Original topic data"
    )
    search_query: str = Field(..., description="Query used for web search")
    search_results: List[SearchResult] = Field(..., description="Web search results")
    summary: str = Field(..., description="AI-generated summary of the topic")
    key_concepts: List[str] = Field(
        ..., description="Key concepts extracted from search"
    )
    related_topics: List[str] = Field(
        ..., description="Related topics for further study"
    )
    study_resources: List[SearchResult] = Field(
        ..., description="Educational resources found"
    )
