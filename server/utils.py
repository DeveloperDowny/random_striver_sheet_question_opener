import logging
import os
from typing import Dict, List

from fastapi import HTTPException
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from db_config import DBConfig
from schemas import SearchResult
from tavily_search_service import TavilySearchService

logger = logging.getLogger(__name__)


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


def generate_related_topics(
        search_results: List[Dict], original_topic: str
) -> List[str]:
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
        "wikipedia.org",
        "edu",
        "coursera.org",
        "edx.org",
        "khanacademy.org",
        "britannica.com",
        "nationalgeographic.com",
        "scientificamerican.com",
    ]

    study_resources = []

    for result in search_results:
        url = result.get("url", "")
        title = result.get("title", "")
        content = result.get("content", "")

        # Check if it's from an educational domain
        is_educational = any(domain in url.lower() for domain in educational_domains)

        # Check if title suggests educational content
        educational_keywords = [
            "tutorial",
            "guide",
            "course",
            "lesson",
            "learn",
            "study",
        ]
        has_educational_keywords = any(
            keyword in title.lower() for keyword in educational_keywords
        )

        if is_educational or has_educational_keywords:
            study_resources.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=content[:200] + "..." if len(content) > 200 else content,
                )
            )

    return study_resources[:5]  # Return top 5 educational resources


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

        words = re.findall(r"\b[a-zA-Z]{4,}\b", snippet + " " + title)

        # Filter for potentially important terms
        important_words = [
            word.title()
            for word in words
            if len(word) > 4
               and word
               not in [
                   "that",
                   "this",
                   "with",
                   "from",
                   "they",
                   "have",
                   "been",
                   "will",
                   "more",
                   "about",
                   "other",
                   "which",
                   "their",
                   "would",
               ]
        ]

        concepts.update(important_words[:3])  # Limit concepts per result

    return list(concepts)[:10]  # Return top 10 concepts


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def get_tavily_service():
    """Dependency to get Tavily search service"""
    return TavilySearchService(TAVILY_API_KEY)
