import asyncio
import aiohttp
import json
from pathlib import Path
import logging
from typing import Optional
from aiohttp import ClientSession, TCPConnector
from asyncio import Semaphore
import random
import aiofiles 

class DataFetcher:
    BASE_URL = "https://www.naukri.com/code360/api/v3/public_section/company_problem_list"
    PARAMS = {
        "slug": "oracle",
        "request_differentiator": "1721714951384",
        "naukri_request": "true"
    }
    TOTAL_PAGES = 53
    MAX_CONCURRENT_REQUESTS = 5
    MAX_RETRIES = 3
    RETRY_DELAY = 5

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session: Optional[ClientSession] = None
        self.semaphore: Optional[Semaphore] = None
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self):
        connector = TCPConnector(limit=self.MAX_CONCURRENT_REQUESTS, ssl=False)
        self.session = ClientSession(connector=connector)
        self.semaphore = Semaphore(self.MAX_CONCURRENT_REQUESTS)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.naukri.com/",
            "Origin": "https://www.naukri.com",
            "DNT": "1",
            "Connection": "keep-alive",
        }

    async def fetch_page(self, page: int) -> dict:
        params = {**self.PARAMS, "page": page}
        for attempt in range(self.MAX_RETRIES):
            try:
                async with self.semaphore:
                    await asyncio.sleep(random.uniform(1, 3))  # Random delay between requests
                    async with self.session.get(self.BASE_URL, params=params, headers=self.get_headers()) as response:
                        response.raise_for_status()
                        return await response.json()
            except aiohttp.ClientError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                self.logger.warning(f"Retrying page {page} (attempt {attempt + 1})")
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))  # Exponential backoff

    async def save_json(self, data: dict, filename: str):
        file_path = self.output_dir / filename
        async with aiofiles.open(file_path, mode='w') as file:
            await file.write(json.dumps(data, indent=2))

    async def process_page(self, page: int):
        try:
            data = await self.fetch_page(page)
            filename = f"page_{page}.json"
            await self.save_json(data, filename)
            self.logger.info(f"Saved data for page {page}")
        except Exception as e:
            self.logger.error(f"Error processing page {page}: {str(e)}")

    async def run(self):
        tasks = [self.process_page(page) for page in range(1, self.TOTAL_PAGES + 1)]
        await asyncio.gather(*tasks)

async def main():
    async with DataFetcher() as fetcher:
        await fetcher.run()

if __name__ == "__main__":
    asyncio.run(main())