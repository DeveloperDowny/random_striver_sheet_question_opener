# -*- coding: utf-8 -*-
"""
Implementation of specific sheet handlers inheriting from SheetHandler.
These handlers now require MongoDB client and database name for initialization.
"""

import logging
from typing import List, Dict, Any, Union
import enum
from pymongo import MongoClient # Import MongoClient for type hinting

# Assuming SheetHandler is defined in sheet_handler.py or accessible
# from sheet_handler import SheetHandler
# Using the definition from the Canvas artifact "sheet_handler_mongo" as the base
from sheet_handler import SheetHandler # Make sure this import points to your updated base class file

logger = logging.getLogger(__name__)

# --- Specific Handler Implementations ---

class SDESheetHandler(SheetHandler):
    """Handler for the SDE sheet."""
    def __init__(self, mongo_client: MongoClient, db_name: str):
        # Pass mongo_client and db_name to the base class constructor
        super().__init__(
            file_name="sde_sheet",
            site="naukri.com",
            mongo_client=mongo_client,
            db_name=db_name
        )

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flattens data specific to the SDE sheet format.
        NOTE: Likely unused if data comes pre-flattened from MongoDB.
        """
        if not isinstance(data, dict) or "sheetData" not in data:
             logger.warning("Invalid data format for SDESheetHandler flatten.")
             return []
        logger.debug("Flattening SDE sheet data.")
        # Original flatten logic - kept for reference or potential use
        try:
            return [item for sublist in data["sheetData"] for item in sublist.get("topics", [])]
        except (TypeError, KeyError) as e:
             logger.error(f"Error during SDE sheet flatten: {e}. Data structure might be unexpected.")
             return []


class CoreSheetHandler(SheetHandler):
    """Handler for core subject sheets (DBMS, OS, CN)."""
    def __init__(self, subject: str, mongo_client: MongoClient, db_name: str):
         # Ensure subject is valid if needed
         if subject not in ["dbms", "os", "cn"]:
              raise ValueError(f"Invalid subject for CoreSheetHandler: {subject}")
         # Pass mongo_client and db_name to the base class constructor
         super().__init__(
              file_name=f"{subject}_core_sheet",
              site="geeksforgeeks.org",
              mongo_client=mongo_client,
              db_name=db_name
         )
         self.subject = subject # Store subject if needed for other methods

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flattens data specific to the Core sheet format.
        NOTE: Likely unused if data comes pre-flattened from MongoDB.
        """
        if not isinstance(data, dict) or "sheetData" not in data:
             logger.warning(f"Invalid data format for CoreSheetHandler flatten (subject: {self.subject}).")
             return []
        logger.debug(f"Flattening core sheet data for {self.subject}.")
        # Original flatten logic - kept for reference or potential use
        try:
            return [item for sublist in data["sheetData"] for item in sublist.get("data", [])]
        except (TypeError, KeyError) as e:
             logger.error(f"Error during Core sheet flatten ({self.subject}): {e}. Data structure might be unexpected.")
             return []


class LeetCodeSQLHandler(SheetHandler):
    """Handler for the LeetCode SQL 50 sheet."""
    def __init__(self, mongo_client: MongoClient, db_name: str):
        # Pass mongo_client and db_name to the base class constructor
        super().__init__(
            file_name="lc_sql_50",
            site="leetcode.com",
            mongo_client=mongo_client,
            db_name=db_name
        )

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flattens data specific to the LeetCode SQL 50 format.
        NOTE: Likely unused if data comes pre-flattened from MongoDB.
        """
        if not isinstance(data, dict) or "sheetData" not in data:
             logger.warning("Invalid data format for LeetCodeSQLHandler flatten.")
             return []
        logger.debug("Flattening LC SQL 50 data.")
        # Original flatten logic - kept for reference or potential use
        try:
            flattened_list = [
                item for sublist in data["sheetData"] for item in sublist.get("questions", [])
            ]
            return flattened_list
        except (TypeError, KeyError) as e:
             logger.error(f"Error during LC SQL 50 flatten: {e}. Data structure might be unexpected.")
             return []


class LeetCodeDSA75Handler(SheetHandler):
    """Handler for the LeetCode DSA 75 sheet."""
    def __init__(self, mongo_client: MongoClient, db_name: str):
        # Pass mongo_client and db_name to the base class constructor
        super().__init__(
            file_name="lc_dsa_75",
            site="leetcode.com",
            mongo_client=mongo_client,
            db_name=db_name
        )

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flattens data specific to the LeetCode DSA 75 format.
        NOTE: Likely unused if data comes pre-flattened from MongoDB.
        """
        if not isinstance(data, dict) or "sheetData" not in data:
             logger.warning("Invalid data format for LeetCodeDSA75Handler flatten.")
             return []
        logger.debug("Flattening LC DSA 75 data.")
        # Original flatten logic - kept for reference or potential use
        try:
            flattened_list = [
                item for sublist in data["sheetData"] for item in sublist.get("questions", [])
            ]
            return flattened_list
        except (TypeError, KeyError) as e:
             logger.error(f"Error during LC DSA 75 flatten: {e}. Data structure might be unexpected.")
             return []


class GFGMustDoProductHandler(SheetHandler):
    """Handler for the GFG Must Do Product sheet."""
    def __init__(self, mongo_client: MongoClient, db_name: str):
        # Pass mongo_client and db_name to the base class constructor
        super().__init__(
            file_name="must_do_product_gfg",
            site="geeksforgeeks.org",
            mongo_client=mongo_client,
            db_name=db_name
        )

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flattens data specific to the GFG Must Do Product format.
        NOTE: Likely unused if data comes pre-flattened from MongoDB.
        """
        if not isinstance(data, dict) or "sheetData" not in data:
             logger.warning("Invalid data format for GFGMustDoProductHandler flatten.")
             return []
        logger.debug("Flattening GFG must do product data.")
        # Original flatten logic - kept for reference or potential use
        # This assumes sheetData is already the list we want
        if isinstance(data["sheetData"], list):
             return data["sheetData"]
        else:
             logger.error("Error during GFG flatten: 'sheetData' is not a list.")
             return []

    # def create_link(self, link: str) -> str: # This overrides base behavior, likely intended if topic["link"] exists
    #     return link


class NaukriDifficulties(enum.Enum):
    """Enum for difficulty levels often found on Naukri/GFG."""
    EASY = "Easy"
    MEDIUM = "Moderate" # Or "Medium" depending on source data
    HARD = "Hard"


class MicrosoftDSAHandler(SheetHandler):
    """Handler for Microsoft DSA questions, potentially using auxiliary JSONs."""
    def __init__(self, mongo_client: MongoClient, db_name: str):
        # Define jsons_path relative to the base handler file location
        # This assumes 'microsoft_question_jsons' is in the parent directory
        # Adjust path as needed based on your project structure
        base_handler_dir = os.path.dirname(os.path.abspath(__file__))
        jsons_dir = os.path.abspath(os.path.join(base_handler_dir, "..", "microsoft_question_jsons"))

        # Pass mongo_client and db_name to the base class constructor
        super().__init__(
            file_name="microsoft_dsa",
            site="naukri.com", # Or geeksforgeeks.org / leetcode.com depending on source
            mongo_client=mongo_client,
            db_name=db_name,
            jsons_path=jsons_dir, # Pass the calculated absolute path
            difficulty=NaukriDifficulties.MEDIUM # Default difficulty
        )
        # self.difficulty is already set in super().__init__

    def get_title(self, topic: Dict[str, Any]) -> str:
        """Gets title, assuming 'name' field exists for these topics."""
        return topic.get("name", "Unknown Title") # Use .get for safety

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flatten logic for Microsoft DSA.
        NOTE: If primary data now comes from Mongo, this might only process
              auxiliary JSONs or might be unused. Adjust as needed.
        """
        logger.debug("Flattening Microsoft DSA data (may use auxiliary JSONs).")
        # This implementation relies on auxiliary JSONs via questions_from_jsons
        # If the main data is now in Mongo, decide how/if to use this.
        # If Mongo data is primary, you might not need this flatten override.
        return self.questions_from_jsons(data if isinstance(data, dict) else {})

import os
class PhonePeDSAHandler(SheetHandler):
    """Handler for PhonePe DSA questions, potentially using auxiliary JSONs."""
    def __init__(self, mongo_client: MongoClient, db_name: str):
        base_handler_dir = os.path.dirname(os.path.abspath(__file__))
        jsons_dir = os.path.abspath(os.path.join(base_handler_dir, "..", "phonepe_question_jsons"))

        # Pass mongo_client and db_name to the base class constructor
        super().__init__(
            file_name="phonepe_dsa",
            site="naukri.com", # Or other relevant site
            mongo_client=mongo_client,
            db_name=db_name,
            jsons_path=jsons_dir,
            difficulty=NaukriDifficulties.MEDIUM
        )

    def get_title(self, topic: Dict[str, Any]) -> str:
        """Gets title, assuming 'name' field exists."""
        return topic.get("name", "Unknown Title")

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flatten logic for PhonePe DSA.
        NOTE: Adjust if primary data source changes from auxiliary JSONs.
        """
        logger.debug("Flattening PhonePe DSA data (may use auxiliary JSONs).")
        return self.questions_from_jsons(data if isinstance(data, dict) else {})


class OracleDSAHandler(SheetHandler):
    """Handler for Oracle DSA questions, potentially using auxiliary JSONs."""
    def __init__(self, mongo_client: MongoClient, db_name: str):
        base_handler_dir = os.path.dirname(os.path.abspath(__file__))
        jsons_dir = os.path.abspath(os.path.join(base_handler_dir, "..", "oracle_question_jsons"))

        # Pass mongo_client and db_name to the base class constructor
        super().__init__(
            file_name="oracle_dsa",
            site="leetcode.com", # Or other relevant site
            mongo_client=mongo_client,
            db_name=db_name,
            jsons_path=jsons_dir,
            difficulty=NaukriDifficulties.MEDIUM
        )

    def get_title(self, topic: Dict[str, Any]) -> str:
        """Gets title, assuming 'name' field exists."""
        return topic.get("name", "Unknown Title")

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flatten logic for Oracle DSA.
        NOTE: Adjust if primary data source changes from auxiliary JSONs.
        """
        logger.debug("Flattening Oracle DSA data (may use auxiliary JSONs).")
        return self.questions_from_jsons(data if isinstance(data, dict) else {})


class LinuxCommandsHandler(SheetHandler):
    """Handler for Linux commands sheet."""
    def __init__(self, mongo_client: MongoClient, db_name: str):
        # Pass mongo_client and db_name to the base class constructor
        super().__init__(
            file_name="linux_commands",
            site="manpages.ubuntu.com", # Or die.net, etc.
            mongo_client=mongo_client,
            db_name=db_name
        )

    def get_title(self, topic: Dict[str, Any]) -> str:
        """Gets title, assuming 'id' field holds the command name."""
        return topic.get("id", "Unknown Command") # Use .get for safety

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flatten logic for Linux commands.
        NOTE: Likely unused if data comes pre-flattened from MongoDB.
        """
        if not isinstance(data, dict) or "data" not in data:
             logger.warning("Invalid data format for LinuxCommandsHandler flatten.")
             return []
        logger.debug("Flattening Linux commands data.")
        # Assumes 'data' key holds the list of commands
        if isinstance(data["data"], list):
            return data["data"]
        else:
            logger.error("Error during Linux commands flatten: 'data' is not a list.")
            return []


class DockerCommandsHandler(SheetHandler):
    """Handler for Docker commands sheet."""
    def __init__(self, mongo_client: MongoClient, db_name: str):
        # Pass mongo_client and db_name to the base class constructor
        super().__init__(
            file_name="docker_commands",
            site="docs.docker.com",
            mongo_client=mongo_client,
            db_name=db_name
        )

    def get_title(self, topic: Dict[str, Any]) -> str:
        """Gets title, assuming 'id' is the command, appends ' command'."""
        command = topic.get("id", "unknown")
        return f"{command} command"

    def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flatten logic for Docker commands.
        NOTE: Likely unused if data comes pre-flattened from MongoDB.
        """
        if not isinstance(data, dict) or "data" not in data:
             logger.warning("Invalid data format for DockerCommandsHandler flatten.")
             return []
        logger.debug("Flattening Docker commands data.")
        # Assumes 'data' key holds the list of commands
        if isinstance(data["data"], list):
            return data["data"]
        else:
            logger.error("Error during Docker commands flatten: 'data' is not a list.")
            return []


class LanggraphHandler(SheetHandler):
     """Handler for Langgraph concepts."""
     def __init__(self, mongo_client: MongoClient, db_name: str):
         # Pass mongo_client and db_name to the base class constructor
         super().__init__(
             file_name="langgraph",
             site="langchain.com", # Or specific langgraph docs site
             mongo_client=mongo_client,
             db_name=db_name
         )

     def get_title(self, topic: Dict[str, Any]) -> str:
         """Gets title, assuming 'id' is the concept, appends ' langgraph'."""
         concept = topic.get("id", "unknown")
         return f"{concept} langgraph"

     def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flatten logic for Langgraph data.
        NOTE: Likely unused if data comes pre-flattened from MongoDB.
        """
        if not isinstance(data, dict) or "data" not in data:
             logger.warning("Invalid data format for LanggraphHandler flatten.")
             return []
        logger.debug("Flattening Langgraph data.")
        # Assumes 'data' key holds the list
        if isinstance(data["data"], list):
            return data["data"]
        else:
            logger.error("Error during Langgraph flatten: 'data' is not a list.")
            return []


class DSACommonPatterns(SheetHandler):
     """Handler for common DSA patterns."""
     def __init__(self, mongo_client: MongoClient, db_name: str):
         # Pass mongo_client and db_name to the base class constructor
         super().__init__(
             file_name="dsa_common_patterns",
             site="naukri.com", # Or leetcode discuss, geeksforgeeks, etc.
             mongo_client=mongo_client,
             db_name=db_name
         )

     def get_title(self, topic: Dict[str, Any]) -> str:
         """Gets title, assuming 'id' field holds the pattern name."""
         return topic.get("id", "Unknown Pattern")

     def flatten(self, data: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """
        Flatten logic for DSA common patterns.
        NOTE: Likely unused if data comes pre-flattened from MongoDB.
        """
        if not isinstance(data, dict) or "data" not in data:
             logger.warning("Invalid data format for DSACommonPatterns flatten.")
             return []
        logger.debug("Flattening DSA common patterns data.")
        # Assumes 'data' key holds the list
        if isinstance(data["data"], list):
            return data["data"]
        else:
            logger.error("Error during DSA patterns flatten: 'data' is not a list.")
            return []

