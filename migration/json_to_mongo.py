# -*- coding: utf-8 -*-
"""
Script to read specified JSON files, flatten their content using specific
sheet handlers, and insert the data into MongoDB collections named after the files.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional, Union
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, BulkWriteError, PyMongoError
from migration.config import Config

# --- IMPORTANT: Assume these imports are available ---
# Make sure sheet_handler_factory.py, sheet_handlers.py, sheet_handler.py
# are in the same directory or installed as a package.
try:
    from sheet_handler_factory import SheetHandlerFactory

    # from sheet_handler import SheetHandler # Optional: if needed for type hinting
except ImportError:
    logging.error(
        "Could not import SheetHandlerFactory. Make sure the necessary handler files are present."
    )

    # You might want to exit here if handlers are essential
    # import sys
    # sys.exit(1)
    # As a fallback for the template, create a dummy factory
    class SheetHandlerFactory:
        @staticmethod
        def create_handler(sheet_type: str):
            raise ValueError(f"Dummy Factory: Cannot create handler for {sheet_type}")


# --- Configuration ---
config = Config(_env_file=r"D:\DPythonProjects\roulette\migration\.env")


# List of JSON files to process (relative paths from BASE_DIRECTORY)
# Extracted from the provided tree.txt structure
JSON_FILES_TO_PROCESS: List[str] = [
    "data/cn_core_sheet.json",
    "data/dbms_core_sheet.json",
    "data/docker_commands.json",
    "data/dsa_common_patterns.json",
    "data/langgraph.json",
    "data/lc_dsa_75.json",
    "data/lc_sql_50.json",
    "data/linux_commands.json",
    "data/microsoft_dsa.json",
    "data/must_do_product_gfg.json",
    "data/oracle_dsa.json",
    "data/os_core_sheet.json",
    "data/phonepe_dsa.json",
    "data/sde_sheet.json",
    "history/cn_core_sheet.json",
    "history/dbms_core_sheet.json",
    "history/docker_commands.json",
    "history/dsa_common_patterns.json",
    "history/langgraph.json",
    "history/lc_dsa_75.json",
    "history/lc_sql_50.json",
    "history/microsoft_dsa.json",
    "history/must_do_product_gfg.json",
    "history/oracle_dsa.json",
    "history/os_core_sheet.json",
    "history/phonepe_dsa.json",
    "history/sde_sheet.json",
    "microsoft_question_jsons/page_1.json",
    "microsoft_question_jsons/page_10.json",
    "microsoft_question_jsons/page_11.json",
    "microsoft_question_jsons/page_12.json",
    "microsoft_question_jsons/page_13.json",
    "microsoft_question_jsons/page_14.json",
    "microsoft_question_jsons/page_15.json",
    "microsoft_question_jsons/page_16.json",
    "microsoft_question_jsons/page_17.json",
    "microsoft_question_jsons/page_18.json",
    "microsoft_question_jsons/page_19.json",
    "microsoft_question_jsons/page_2.json",
    "microsoft_question_jsons/page_20.json",
    "microsoft_question_jsons/page_21.json",
    "microsoft_question_jsons/page_22.json",
    "microsoft_question_jsons/page_23.json",
    "microsoft_question_jsons/page_24.json",
    "microsoft_question_jsons/page_25.json",
    "microsoft_question_jsons/page_26.json",
    "microsoft_question_jsons/page_27.json",
    "microsoft_question_jsons/page_28.json",
    "microsoft_question_jsons/page_29.json",
    "microsoft_question_jsons/page_3.json",
    "microsoft_question_jsons/page_30.json",
    "microsoft_question_jsons/page_31.json",
    "microsoft_question_jsons/page_32.json",
    "microsoft_question_jsons/page_33.json",
    "microsoft_question_jsons/page_34.json",
    "microsoft_question_jsons/page_35.json",
    "microsoft_question_jsons/page_36.json",
    "microsoft_question_jsons/page_37.json",
    "microsoft_question_jsons/page_38.json",
    "microsoft_question_jsons/page_39.json",
    "microsoft_question_jsons/page_4.json",
    "microsoft_question_jsons/page_40.json",
    "microsoft_question_jsons/page_41.json",
    "microsoft_question_jsons/page_42.json",
    "microsoft_question_jsons/page_43.json",
    "microsoft_question_jsons/page_44.json",
    "microsoft_question_jsons/page_45.json",
    "microsoft_question_jsons/page_46.json",
    "microsoft_question_jsons/page_47.json",
    "microsoft_question_jsons/page_48.json",
    "microsoft_question_jsons/page_49.json",
    "microsoft_question_jsons/page_5.json",
    "microsoft_question_jsons/page_50.json",
    "microsoft_question_jsons/page_51.json",
    "microsoft_question_jsons/page_52.json",
    "microsoft_question_jsons/page_53.json",
    "microsoft_question_jsons/page_6.json",
    "microsoft_question_jsons/page_7.json",
    "microsoft_question_jsons/page_8.json",
    "microsoft_question_jsons/page_9.json",
    "oracle_question_jsons/page_1.json",
    "oracle_question_jsons/page_10.json",
    "oracle_question_jsons/page_11.json",
    "oracle_question_jsons/page_12.json",
    "oracle_question_jsons/page_13.json",
    "oracle_question_jsons/page_14.json",
    "oracle_question_jsons/page_15.json",
    "oracle_question_jsons/page_16.json",
    "oracle_question_jsons/page_17.json",
    "oracle_question_jsons/page_18.json",
    "oracle_question_jsons/page_19.json",
    "oracle_question_jsons/page_2.json",
    "oracle_question_jsons/page_3.json",
    "oracle_question_jsons/page_4.json",
    "oracle_question_jsons/page_5.json",
    "oracle_question_jsons/page_6.json",
    "oracle_question_jsons/page_7.json",
    "oracle_question_jsons/page_8.json",
    "oracle_question_jsons/page_9.json",
    "phonepe_question_jsons/page_1.json",
    "phonepe_question_jsons/page_2.json",
    "phonepe_question_jsons/page_3.json",
    "phonepe_question_jsons/page_4.json",
    "phonepe_question_jsons/page_5.json",
    "phonepe_question_jsons/page_6.json",
    "phonepe_question_jsons/page_7.json",
]

# --- Logging Setup ---


def setup_logging() -> None:
    """Configures logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename="json_to_mongo.log",
    )


# --- MongoDB Functions ---


def connect_to_mongodb(uri: str, db_name: str) -> Optional[MongoClient]:
    """
    Establishes a connection to the MongoDB database.

    Args:
        uri: The MongoDB connection string.
        db_name: The name of the database to connect to.

    Returns:
        A MongoClient instance if connection is successful, None otherwise.
    """
    try:
        client = MongoClient(uri)
        # The ismaster command is cheap and does not require auth.
        client.admin.command("ismaster")
        logging.info(f"Successfully connected to MongoDB. Using database: '{db_name}'")
        return client
    except ConnectionFailure:
        logging.exception(f"Failed to connect to MongoDB at {uri}")
        return None
    except Exception as e:
        logging.exception(
            f"An unexpected error occurred during MongoDB connection: {e}"
        )
        return None


def get_collection_name(file_path: str) -> str:
    """
    Derives the MongoDB collection name from the JSON file path.
    (Filename without extension).

    Args:
        file_path: The relative path to the JSON file.

    Returns:
        The derived collection name.
    """
    # Get the filename without extension
    base_name = os.path.basename(file_path)
    collection_name, _ = os.path.splitext(base_name)
    # Optional: Sanitize the name if needed (e.g., replace dots, spaces)
    # collection_name = collection_name.replace('.', '_').replace(' ', '_')
    return collection_name


# --- Data Processing Functions ---


def flatten_json_data(
    data: Union[Dict[str, Any], List[Any]], collection_name: str
) -> List[Dict[str, Any]]:
    """
    Flattens the JSON data using a specific handler based on the collection name.

    Args:
        data: The parsed JSON data (either a dict or a list).
        collection_name: The name of the target collection, used to determine the handler.

    Returns:
        A list of dictionaries flattened according to the specific handler's logic.
        Returns an empty list if no handler is found or an error occurs.
    """
    try:
        # Use the collection_name as the sheet_type for the factory
        handler = SheetHandlerFactory.create_handler(
            collection_name,
        )
        logging.info(
            f"Using handler '{type(handler).__name__}' for collection '{collection_name}'"
        )
        # Assuming the handler's flatten method takes the parsed data
        flattened_data = handler.flatten(data)

        # Basic validation: ensure the handler returned a list of dicts
        if not isinstance(flattened_data, list):
            logging.error(
                f"Handler '{type(handler).__name__}' for '{collection_name}' did not return a list. Returned type: {type(flattened_data)}. Skipping."
            )
            return []

        valid_items = []
        for i, item in enumerate(flattened_data):
            if isinstance(item, dict):
                valid_items.append(item)
            else:
                logging.warning(
                    f"Item at index {i} returned by handler '{type(handler).__name__}' for '{collection_name}' is not a dictionary. Skipping item."
                )
        return valid_items

    except ValueError as ve:
        # Handle cases where the factory doesn't have a handler for this sheet_type/collection_name
        logging.warning(
            f"No specific handler found for sheet type '{collection_name}': {ve}. Skipping file."
        )
        # Decide fallback behavior: maybe insert raw data if it's simple?
        # For now, we skip if no handler is found.
        # If you want a default behavior (like the previous flatten):
        # if isinstance(data, list): return [d for d in data if isinstance(d, dict)]
        # if isinstance(data, dict): return [data]
        return []
    except ImportError:
        # This might happen if the dummy factory is used because imports failed
        logging.error(
            f"Cannot flatten data for '{collection_name}' due to missing handler imports."
        )
        return []
    except Exception as e:
        # Catch errors within the handler's flatten method
        logging.exception(
            f"Error during flattening by handler for '{collection_name}': {e}"
        )
        return []


def process_json_file(file_path: str, db_client: MongoClient, db_name: str) -> None:
    """
    Reads a JSON file, processes its content using handlers, and inserts it into MongoDB.

    Args:
        file_path: The relative path to the JSON file.
        db_client: The active MongoClient instance.
        db_name: The name of the target database.
    """
    full_path = os.path.join(config.BASE_DIRECTORY, file_path)
    logging.info(f"Processing file: {file_path}")

    # 1. Read the file
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
            # Handle potential empty files
            if not raw_content.strip():
                logging.warning(f"File is empty: {file_path}. Skipping.")
                return
            json_data = json.loads(raw_content)
    except FileNotFoundError:
        logging.error(f"File not found: {full_path}. Skipping.")
        return
    except json.JSONDecodeError:
        logging.exception(f"Invalid JSON format in file: {full_path}. Skipping.")
        return
    except IOError as e:
        logging.exception(f"Error reading file {full_path}: {e}. Skipping.")
        return
    except Exception as e:
        logging.exception(
            f"An unexpected error occurred reading {full_path}: {e}. Skipping."
        )
        return

    # 2. Determine collection name (needed for handler selection)
    collection_name = get_collection_name(file_path)

    # 3. Flatten the data using the appropriate handler
    documents_to_insert = flatten_json_data(json_data, collection_name)
    if not documents_to_insert:
        # Logging is handled within flatten_json_data if issues occur
        logging.info(
            f"No documents to insert for {file_path} after attempting flattening."
        )
        return

    # 4. Get collection and insert
    try:
        db = db_client[db_name]
        collection: Collection = db[collection_name]
        logging.info(
            f"Inserting {len(documents_to_insert)} document(s) into collection: '{collection_name}'"
        )

        # Using insert_many for efficiency
        result = collection.insert_many(
            documents_to_insert, ordered=False
        )  # ordered=False allows partial inserts on error
        logging.info(
            f"Successfully inserted {len(result.inserted_ids)} document(s) into '{collection_name}'."
        )

    except BulkWriteError as bwe:
        logging.error(
            f"Bulk write error inserting into '{collection_name}': {len(bwe.details.get('writeErrors', []))} errors."
        )
        # Log details of write errors if needed
        # for error in bwe.details.get('writeErrors', []):
        #     logging.debug(f"  - Index: {error.get('index')}, Code: {error.get('code')}, Message: {error.get('errmsg')}")
    except PyMongoError as pe:
        logging.exception(
            f"MongoDB error during insertion into '{collection_name}': {pe}"
        )
    except Exception as e:
        logging.exception(
            f"An unexpected error occurred during insertion into '{collection_name}': {e}"
        )


# --- Main Execution ---


def main() -> None:
    """Main function to orchestrate the JSON import process."""
    setup_logging()
    logging.info("Starting JSON to MongoDB import script.")

    mongo_client = connect_to_mongodb(config.MONGODB_URI, config.DATABASE_NAME)
    if not mongo_client:
        logging.error("Exiting script due to MongoDB connection failure.")
        return

    processed_count = 0
    error_count = 0

    for json_file in JSON_FILES_TO_PROCESS:
        try:
            from pathlib import Path

            base_path = Path(r"D:\DPythonProjects\roulette")
            json_file = base_path / json_file

            process_json_file(json_file, mongo_client, config.DATABASE_NAME)
            processed_count += 1
        except Exception as e:
            # Catch unexpected errors in process_json_file loop itself
            logging.exception(f"Unexpected error processing file {json_file}: {e}")
            error_count += 1

    logging.info("-" * 30)
    logging.info(
        f"Script finished. Attempted to process {len(JSON_FILES_TO_PROCESS)} files."
    )
    logging.info(f"Successfully processed loop for: {processed_count} files.")
    logging.info(f"Encountered errors during loop for: {error_count} files.")
    logging.info("-" * 30)

    # Close the MongoDB connection
    if mongo_client:
        mongo_client.close()
        logging.info("MongoDB connection closed.")


if __name__ == "__main__":
    main()
