# -*- coding: utf-8 -*-
"""
Abstract base class for handling different types of sheets (e.g., SDE, Core subjects),
fetching data from MongoDB, and processing it to select a random topic.
History and revision tracking now also use MongoDB instead of local files.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import json
import logging
import random
import urllib.parse
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

import os


# Assuming Config class exists and provides kDebugMode
# from config import Config
class Config:
    kDebugMode = False  # Placeholder


logger = logging.getLogger(__name__)  # Use __name__ for logger


class SheetHandler(ABC):
    """
    Abstract base class for sheet handlers. Fetches data from MongoDB.
    Handles history and revision tracking using MongoDB collections.
    """

    def __init__(
        self,
        file_name: str,
        site: str,
        mongo_client: MongoClient,
        db_name: str,
        jsons_path: Optional[str] = None,
        difficulty: Optional[Any] = None,
    ):
        """
        Initializes the SheetHandler.

        Args:
            file_name (str): The base name for the sheet (used as collection name).
            site (str): The website domain for creating search links (e.g., "leetcode.com").
            mongo_client (MongoClient): An active PyMongo client instance.
            db_name (str): The name of the MongoDB database containing the collections.
            jsons_path (Optional[str]): Path for specific handlers needing extra JSONs. Defaults to None.
            difficulty (Optional[Any]): Difficulty level for specific handlers. Defaults to None.
        """
        if not mongo_client:
            raise ValueError("mongo_client cannot be None")
        if not db_name:
            raise ValueError("db_name cannot be empty")

        self.file_name = file_name  # This will be used as the collection name
        self.site = site
        self.mongo_client = mongo_client
        self.db_name = db_name
        self.jsons_path = jsons_path  # Keep for handlers that might still need it
        self.difficulty = difficulty  # Keep for handlers that might still need it

        # Get MongoDB database
        self.db = self.mongo_client[self.db_name]

        # Set collection names for data, history, and revision
        self.data_collection_name = self.file_name
        self.history_collection_name = "history"
        self.revision_collection_name = "revision"

        # Ensure collections exist
        self._ensure_collections_exist()

        self.should_allow_repeats = False

    def _ensure_collections_exist(self):
        """Ensures that the necessary collections exist in the database."""
        collection_names = self.db.list_collection_names()

        # Create collections if they don't exist
        if self.history_collection_name not in collection_names:
            self.db.create_collection(self.history_collection_name)
            logger.info(f"Created history collection: {self.history_collection_name}")

        if self.revision_collection_name not in collection_names:
            self.db.create_collection(self.revision_collection_name)
            logger.info(f"Created revision collection: {self.revision_collection_name}")

    @abstractmethod
    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Abstract method for flattening data.
        Kept for potential subclass use or future refactoring.
        """
        pass

    def get_all_jsons(self) -> List[str]:
        """Gets all JSON filenames from the specific jsons_path."""
        if not self.jsons_path or not os.path.exists(self.jsons_path):
            logger.warning(f"jsons_path not set or does not exist for {self.file_name}")
            return []
        try:
            files = [
                f for f in os.listdir(self.jsons_path) if f.lower().endswith(".json")
            ]
            return files
        except OSError as e:
            logger.error(f"Error listing directory {self.jsons_path}: {e}")
            return []

    def pick_random_json(self) -> Optional[str]:
        """Picks a random JSON file from the jsons_path."""
        files = self.get_all_jsons()
        return random.choice(files) if files else None

    def get_json(self, file: str) -> Optional[Dict[str, Any]]:
        """Loads data from a specific JSON file in jsons_path."""
        if not self.jsons_path or not file:
            return None
        file_path = os.path.join(self.jsons_path, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            logger.error(f"Auxiliary JSON file not found: {file_path}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in auxiliary file: {file_path}")
            return None
        except Exception as e:
            logger.exception(f"Error reading auxiliary JSON file {file_path}: {e}")
            return None

    def questions_from_jsons(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Example method for handlers that load questions from auxiliary JSONs.
        """
        files = self.get_all_jsons()
        data_array = []
        data_array = [self.get_json(file) for file in files]
        questions_array = []

        for data in data_array:
            if not data or "data" not in data or "problem_list" not in data["data"]:
                logger.warning(
                    f"Invalid structure in auxiliary JSON {files} for {self.file_name}"
                )
                return []

            logger.debug(f"Processing auxiliary JSON {files} for {self.file_name}")
            questions = data["data"]["problem_list"]
            if self.difficulty:
                questions = [
                    item
                    for item in questions
                    if item.get("difficulty") == self.difficulty.value
                ]
            questions_array.extend(questions)
        return questions_array

    def _read_history(self) -> List[str]:
        """
        Reads the list of solved IDs from MongoDB history collection.
        """
        try:
            # Query the history collection for documents related to this sheet
            history_collection = self.db[self.history_collection_name]
            history_doc = history_collection.find_one({"sheet_name": self.file_name})

            if not history_doc:
                # Create a new history document if none exists
                logger.info(
                    f"No history found for {self.file_name}. Creating new history."
                )
                history_collection.insert_one(
                    {"sheet_name": self.file_name, "solved_ids": []}
                )
                return []

            # Ensure solved_ids exists and is a list
            if "solved_ids" not in history_doc or not isinstance(
                history_doc["solved_ids"], list
            ):
                logger.warning(
                    f"Invalid history format for {self.file_name}. Resetting history."
                )
                history_collection.update_one(
                    {"sheet_name": self.file_name}, {"$set": {"solved_ids": []}}
                )
                return []

            # Convert all IDs to strings for consistency
            return [str(id_val) for id_val in history_doc["solved_ids"]]

        except PyMongoError as e:
            logger.exception(f"MongoDB error reading history for {self.file_name}: {e}")
            return []
        except Exception as e:
            logger.exception(
                f"Unexpected error reading history for {self.file_name}: {e}"
            )
            return []

    def remove_solved(
        self, sheet_data: List[Dict[str, Any]], solved_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Removes items from sheet_data whose 'id' is present in solved_ids."""
        logger.debug(f"Removing {len(solved_ids)} solved items from sheet data.")
        solved_set = set(solved_ids)  # Convert list to set for efficient lookup
        return [
            item for item in sheet_data if str(item.get("id", None)) not in solved_set
        ]

    def get_random_topic(
        self, filtered_data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Selects a random topic from the filtered list."""
        if not filtered_data:
            logger.warning(f"No topics available for {self.file_name} after filtering.")
            return None
        try:
            return random.choice(filtered_data)
        except IndexError:
            logger.error("IndexError during random choice, though list was not empty.")
            return None

    def create_link(self, title: str) -> str:
        """Creates a Google search link for the topic title on the specified site."""
        url_safe_title = urllib.parse.quote_plus(title)
        return f"https://www.google.com/search?q={url_safe_title}+site%3A{self.site}"

    def update_history(self, history: List[str], new_id: str) -> None:
        """
        Updates the history in MongoDB with a new ID.

        Args:
            history (List[str]): Current list of solved IDs (not used directly)
            new_id (str): New ID to add to history
        """
        if Config.kDebugMode:
            logger.info("Debug mode enabled. Skipping history update.")
            return
        if new_id is None:
            logger.warning("Attempted to add None ID to history. Skipping.")
            return

        new_id_str = str(new_id)  # Ensure ID is a string

        try:
            # Update the history document in MongoDB
            history_collection = self.db[self.history_collection_name]
            result = history_collection.update_one(
                {"sheet_name": self.file_name},
                {
                    "$addToSet": {"solved_ids": new_id_str}
                },  # $addToSet prevents duplicates
            )

            if result.matched_count == 0:
                # Create a new document if none exists
                history_collection.insert_one(
                    {"sheet_name": self.file_name, "solved_ids": [new_id_str]}
                )

            logger.info(f"History updated with ID: {new_id_str}")

        except PyMongoError as e:
            logger.exception(
                f"MongoDB error updating history for {self.file_name}: {e}"
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error updating history for {self.file_name}: {e}"
            )

    def get_title(self, topic: Dict[str, Any]) -> str:
        """Extracts the title from the topic dictionary."""
        return topic.get("title", "Unknown Title")

    def process(self) -> None:
        """
        Main processing logic using MongoDB for all data operations.
        """
        logger.info(
            f"Processing sheet: {self.file_name} (Collection: {self.file_name})"
        )

        # 1. Fetch data from MongoDB
        sheet_data_from_db: List[Dict[str, Any]] = []
        try:
            collection: Collection = self.db[self.file_name]
            sheet_data_from_db = list(collection.find({}))
            if not sheet_data_from_db:
                logger.warning(
                    f"No data found in MongoDB collection: '{self.file_name}'"
                )
                return

        except PyMongoError as pe:
            logger.exception(
                f"MongoDB error fetching data for collection '{self.file_name}': {pe}"
            )
            return
        except Exception as e:
            logger.exception(
                f"Unexpected error fetching data for collection '{self.file_name}': {e}"
            )
            return

        # 2. Read history from MongoDB
        history = self._read_history()

        # 3. Filter out solved items
        filtered_data = self.remove_solved(sheet_data_from_db, history)

        # 4. Select a random topic
        random_topic = self.get_random_topic(filtered_data)

        if random_topic is None:
            logger.info(f"No unsolved topics remaining for {self.file_name}.")
            return

        # Ensure the selected topic has an ID
        topic_id = random_topic.get("id", None)
        if topic_id is None:
            logger.error(
                f"Selected random topic for {self.file_name} is missing an 'id' field: {random_topic}"
            )
            return

        topic_id_str = str(topic_id)

        # 5. Check for repeats (safeguard)
        if topic_id_str in history and not self.should_allow_repeats:
            logger.warning(
                f"Repeat ID '{topic_id_str}' found unexpectedly after filtering."
            )
            return

        # 6. Log, create link, update history
        logger.info(f"Selected topic: {random_topic}")
        title = self.get_title(random_topic)
        link = self.create_link(title)
        logger.info(f"Link: {link}")

        # Update history before asking for revision input
        self.update_history(history, topic_id_str)

        # 7. Handle revision marking
        try:
            should_mark_for_revision = (
                input("Mark for revision? (y/n): ").strip().lower()
            )
            if should_mark_for_revision == "y":
                self.mark_revision(topic_id_str)
        except EOFError:
            logger.warning(
                "EOF encountered while waiting for revision input. Skipping revision marking."
            )
        except Exception as e:
            logger.exception(f"Error during revision input/marking: {e}")

    def mark_revision(self, revision_id: str) -> None:
        """
        Marks an item for revision in MongoDB and removes it from history.

        Args:
            revision_id (str): ID to mark for revision
        """
        if Config.kDebugMode:
            logger.info("Debug mode enabled. Skipping revision marking.")
            return

        if not revision_id:
            logger.warning("Cannot mark for revision: ID is empty.")
            return

        try:
            # 1. Add to revision collection
            revision_collection = self.db[self.revision_collection_name]
            revision_doc = revision_collection.find_one({"sheet_name": self.file_name})

            if revision_doc:
                # Update existing document
                revision_collection.update_one(
                    {"sheet_name": self.file_name},
                    {"$addToSet": {"revision_ids": revision_id}},
                )
            else:
                # Create new document
                revision_collection.insert_one(
                    {"sheet_name": self.file_name, "revision_ids": [revision_id]}
                )

            logger.info(f"ID '{revision_id}' marked for revision.")

            # 2. Remove from history collection
            history_collection = self.db[self.history_collection_name]
            history_collection.update_one(
                {"sheet_name": self.file_name}, {"$pull": {"solved_ids": revision_id}}
            )

            logger.info(f"ID '{revision_id}' removed from history.")

        except PyMongoError as e:
            logger.exception(
                f"MongoDB error marking revision for {self.file_name}: {e}"
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error marking revision for {self.file_name}: {e}"
            )
