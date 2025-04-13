# -*- coding: utf-8 -*-
"""
Abstract base class for handling different types of sheets (e.g., SDE, Core subjects),
fetching data from MongoDB, and processing it to select a random topic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import json
import logging
import os
import random
import urllib.parse
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError


# Assuming Config class exists and provides kDebugMode
# from config import Config
class Config:
    kDebugMode = False  # Placeholder


logger = logging.getLogger(__name__)  # Use __name__ for logger


class SheetHandler(ABC):
    """
    Abstract base class for sheet handlers. Fetches data from MongoDB.
    Handles history and revision tracking using local files.
    """

    def __init__(
        self,
        file_name: str,
        site: str,
        mongo_client: MongoClient,  # Added MongoDB client
        db_name: str,  # Added Database name
        jsons_path: Optional[str] = None,
        difficulty: Optional[Any] = None,  # Consider using an Enum for difficulty
    ):
        """
        Initializes the SheetHandler.

        Args:
            file_name (str): The base name for the sheet (used as collection name).
            site (str): The website domain for creating search links (e.g., "leetcode.com").
            mongo_client (MongoClient): An active PyMongo client instance.
            db_name (str): The name of the MongoDB database containing the collections.
            jsons_path (Optional[str]): Path for specific handlers needing extra JSONs (e.g., MicrosoftDSAHandler). Defaults to None.
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

        # History and revision still use local files relative to this script's location
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.history_file_path = os.path.join(
            self.base_dir, f"history/{file_name}.json"
        )
        self.revision_file_path = os.path.join(
            self.base_dir, f"revision/{file_name}.txt"
        )

        # Ensure history/revision directories exist
        os.makedirs(os.path.dirname(self.history_file_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.revision_file_path), exist_ok=True)

        self.should_allow_repeats = False

    @abstractmethod
    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Abstract method for flattening data.
        NOTE: This is likely NO LONGER CALLED in the main `process` flow
              if data from MongoDB is already considered flat.
              It's kept for potential subclass use or future refactoring.
        """
        pass

    # --- Methods potentially kept for specific handlers (like MicrosoftDSAHandler) ---
    # These might need refactoring if their data source also moves to Mongo
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
        Needs to be implemented properly in subclasses like MicrosoftDSAHandler if used.
        """
        # This implementation is specific and might belong in the subclass
        # Keeping structure for reference
        # random_json_file = self.pick_random_json()
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

            logger.debug(
                f"Processing auxiliary JSON {files} for {self.file_name}"
            )
            questions = data["data"]["problem_list"]
            if self.difficulty:
                questions = [
                    item
                    for item in questions
                    if item.get("difficulty")
                    == self.difficulty.value  # Use .get for safety
                ]
            questions_array.extend(questions)
        return questions_array

    # --- End of potentially specific methods ---

    def _read_history(self) -> List[str]:
        """Reads the list of solved IDs from the local history file."""
        try:
            if not os.path.exists(self.history_file_path):
                logger.warning(
                    f"History file not found: {self.history_file_path}. Starting with empty history."
                )
                # Create an empty history file
                with open(self.history_file_path, "w", encoding="utf-8") as file:
                    json.dump({"solved_ids": []}, file, indent=2)
                return []

            with open(self.history_file_path, "r", encoding="utf-8") as file:
                content = file.read()
                if not content.strip():  # Handle empty file
                    logger.warning(
                        f"History file is empty: {self.history_file_path}. Starting with empty history."
                    )
                    return []
                history_data = json.loads(content)
                # Validate structure
                if (
                    isinstance(history_data, dict)
                    and "solved_ids" in history_data
                    and isinstance(history_data["solved_ids"], list)
                ):
                    # Ensure IDs are strings for consistency
                    return [str(id_val) for id_val in history_data["solved_ids"]]
                else:
                    logger.error(
                        f"Invalid format in history file: {self.history_file_path}. Expected {{'solved_ids': [...]}}. Starting fresh."
                    )
                    return []
        except json.JSONDecodeError:
            logger.exception(
                f"Error decoding JSON from history file: {self.history_file_path}. Starting fresh."
            )
            return []
        except IOError as e:
            logger.exception(
                f"Error reading history file {self.history_file_path}: {e}. Starting fresh."
            )
            return []
        except Exception as e:
            logger.exception(
                f"Unexpected error reading history file {self.history_file_path}: {e}. Starting fresh."
            )
            return []

    def remove_solved(
        self, sheet_data: List[Dict[str, Any]], solved_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Removes items from sheet_data whose 'id' is present in solved_ids."""
        logger.debug(f"Removing {len(solved_ids)} solved items from sheet data.")
        solved_set = set(solved_ids)  # Convert list to set for efficient lookup
        # Ensure item["id"] exists and convert to string for comparison
        return [
            item
            for item in sheet_data
            if str(item.get("id", None))
            not in solved_set  # Use .get and str() for safety
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
        except (
            IndexError
        ):  # Should not happen if filtered_data is not empty, but good practice
            logger.error("IndexError during random choice, though list was not empty.")
            return None

    def create_link(self, title: str) -> str:
        """Creates a Google search link for the topic title on the specified site."""
        # URL encodes the title to handle special characters
        url_safe_title = urllib.parse.quote_plus(title)
        # Constructs the search URL
        return f"https://www.google.com/search?q={url_safe_title}+site%3A{self.site}"

    def update_history(self, history: List[str], new_id: str) -> None:
        """Appends the new ID to the history list and saves it to the local file."""
        if Config.kDebugMode:
            logger.info("Debug mode enabled. Skipping history update.")
            return
        if new_id is None:
            logger.warning("Attempted to add None ID to history. Skipping.")
            return

        new_id_str = str(new_id)  # Ensure ID is a string
        history.append(new_id_str)
        try:
            with open(self.history_file_path, "w", encoding="utf-8") as file:
                json.dump({"solved_ids": history}, file, indent=2)
            logger.info(f"History updated with ID: {new_id_str}")
        except IOError as e:
            logger.exception(
                f"Error writing history file {self.history_file_path}: {e}"
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error writing history file {self.history_file_path}: {e}"
            )

    def get_title(self, topic: Dict[str, Any]) -> str:
        """Extracts the title from the topic dictionary."""
        # Use .get for safer access, provide a default title if missing
        return topic.get("title", "Unknown Title")

    def process(self) -> None:
        """
        Main processing logic:
        1. Fetches data from the MongoDB collection.
        2. Reads history from the local file.
        3. Filters out solved items.
        4. Selects a random unsolved topic.
        5. Creates a search link.
        6. Updates history (local file).
        7. Handles revision marking (local files).
        """
        logger.info(
            f"Processing sheet: {self.file_name} (Collection: {self.file_name})"
        )

        # 1. Fetch data from MongoDB
        sheet_data_from_db: List[Dict[str, Any]] = []
        try:
            db = self.mongo_client[self.db_name]
            collection: Collection = db[
                self.file_name
            ]  # Use file_name as collection name
            # Find all documents in the collection
            sheet_data_from_db = list(collection.find({}))  # Convert cursor to list
            if not sheet_data_from_db:
                logger.warning(
                    f"No data found in MongoDB collection: '{self.file_name}'"
                )
                # Decide if you want to stop or continue with empty data
                # return # Option to stop if no data

        except PyMongoError as pe:
            logger.exception(
                f"MongoDB error fetching data for collection '{self.file_name}': {pe}"
            )
            return  # Stop processing if DB error occurs
        except Exception as e:
            logger.exception(
                f"Unexpected error fetching data for collection '{self.file_name}': {e}"
            )
            return  # Stop processing

        # 2. Read history from local file
        history = self._read_history()

        # 3. Filter out solved items
        # Data from Mongo is assumed flat, skip self.flatten()
        filtered_data = self.remove_solved(sheet_data_from_db, history)

        # 4. Select a random topic
        random_topic = self.get_random_topic(filtered_data)

        if random_topic is None:
            logger.info(f"No unsolved topics remaining for {self.file_name}.")
            # Maybe add logic here if all topics are solved?
            return

        # Ensure the selected topic has an ID
        topic_id = random_topic.get("id", None)
        if topic_id is None:
            logger.error(
                f"Selected random topic for {self.file_name} is missing an 'id' field: {random_topic}"
            )
            # Maybe try picking another one? For now, stop.
            return

        topic_id_str = str(topic_id)  # Use string version for comparisons and history

        # 5. Check for repeats (should be rare now if filtering works, but keep as safeguard)
        if topic_id_str in history and not self.should_allow_repeats:
            logger.warning(
                f"Repeat ID '{topic_id_str}' found unexpectedly after filtering. Check filtering logic or history."
            )
            # Potentially add logic to re-pick or handle this scenario
            return  # Avoid infinite loops

        # 6. Log, create link, update history
        # logger.info(f"Selected topic: {json.dumps(random_topic, indent=2)}")
        logger.info(f"Selected topic: {random_topic}")
        title = self.get_title(random_topic)
        link = self.create_link(title)
        logger.info(f"Link: {link}")

        # Update history *before* asking for revision input
        self.update_history(history, topic_id_str)  # Pass the string ID

        # 7. Handle revision marking
        try:
            should_mark_for_revision = (
                input("Mark for revision? (y/n): ").strip().lower()
            )
            if should_mark_for_revision == "y":
                # Pass the *current* history state (which includes the new ID)
                self.mark_revision(history)
        except EOFError:
            logger.warning(
                "EOF encountered while waiting for revision input. Skipping revision marking."
            )
        except Exception as e:
            logger.exception(f"Error during revision input/marking: {e}")

    def mark_revision(self, current_history: List[str]) -> None:
        """Marks the last added item for revision."""
        if Config.kDebugMode:
            logger.info("Debug mode enabled. Skipping revision marking.")
            return

        if not current_history:
            logger.warning("Cannot mark for revision: history is empty.")
            return

        # The ID to mark for revision is the last one added
        revision_id = current_history[-1]

        # 1. Add to revision file
        try:
            with open(self.revision_file_path, "a", encoding="utf-8") as file:
                file.write(revision_id + "\n")
            logger.info(f"ID '{revision_id}' marked for revision.")
        except IOError as e:
            logger.exception(
                f"Error writing revision file {self.revision_file_path}: {e}"
            )
            # Continue to update history even if revision file fails
        except Exception as e:
            logger.exception(
                f"Unexpected error writing revision file {self.revision_file_path}: {e}"
            )

        # 2. Remove the ID from the current history list (as it was just added)
        #    and save the *corrected* history.
        history_without_revision = current_history[
            :-1
        ]  # Create a new list without the last element
        try:
            with open(self.history_file_path, "w", encoding="utf-8") as file:
                json.dump({"solved_ids": history_without_revision}, file, indent=2)
            logger.info(f"History reverted to exclude revision ID '{revision_id}'.")
        except IOError as e:
            logger.exception(
                f"Error reverting history file {self.history_file_path} after revision marking: {e}"
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error reverting history file {self.history_file_path}: {e}"
            )
