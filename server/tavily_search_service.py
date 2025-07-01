import logging
from typing import List, Dict, Any

import httpx
from fastapi import HTTPException

# Tavily API configuration
TAVILY_BASE_URL = "https://api.tavily.com"

logger = logging.getLogger(__name__)


class TavilySearchService:
    """Service for interacting with Tavily search API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = TAVILY_BASE_URL

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Perform web search using Tavily API"""
        if not self.api_key:
            raise HTTPException(status_code=500, detail="Tavily API key not configured")

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
            "exclude_domains": [],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search", headers=headers, json=payload
                )

                if response.status_code != 200:
                    logger.error(
                        f"Tavily API error: {response.status_code} - {response.text}"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Search service error: {response.status_code}",
                    )

                return response.json()

        except httpx.TimeoutException:
            logger.error("Tavily API timeout")
            raise HTTPException(status_code=504, detail="Search service timeout")
        except Exception as e:
            logger.error(f"Tavily API error: {str(e)}")
            raise HTTPException(status_code=500, detail="Search service unavailable")
