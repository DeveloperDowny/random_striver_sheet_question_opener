# -*- coding: utf-8 -*-
"""
Factory class to create appropriate SheetHandler instances based on sheet type.
Now requires MongoDB client and database name to pass to handlers.
"""

from typing import List, Dict, Any # Keep Any if base SheetHandler uses it, else refine
from pymongo import MongoClient # Import MongoClient for type hinting

# Assuming SheetHandler base class and specific handlers are importable
# Ensure these imports point to the updated files from previous steps
# from sheet_handler_mongo import SheetHandler
# from sheet_handlers_mongo import (
#     SDESheetHandler, CoreSheetHandler, LeetCodeDSA75Handler, LeetCodeSQLHandler,
#     GFGMustDoProductHandler, MicrosoftDSAHandler, PhonePeDSAHandler, OracleDSAHandler,
#     LinuxCommandsHandler, DockerCommandsHandler, DSACommonPatterns, LanggraphHandler
# )

# Placeholder imports if the actual files are not available in this context
# Replace with your actual imports
try:
    from sheet_handler import SheetHandler
    from sheet_handlers import (
        SDESheetHandler, CoreSheetHandler, LeetCodeDSA75Handler, LeetCodeSQLHandler,
        GFGMustDoProductHandler, MicrosoftDSAHandler, PhonePeDSAHandler, OracleDSAHandler,
        LinuxCommandsHandler, DockerCommandsHandler, DSACommonPatterns, LanggraphHandler
    )
except ImportError:
    print("Warning: Could not import actual SheetHandler classes. Using placeholders.")
    # Define placeholder classes if imports fail, so the factory structure is valid
    class SheetHandler: # Placeholder Base
        def __init__(self, *, file_name, site, mongo_client, db_name, **kwargs): pass
    class SDESheetHandler(SheetHandler): pass
    class CoreSheetHandler(SheetHandler):
        def __init__(self, *, subject, mongo_client, db_name, **kwargs):
             super().__init__(file_name=f"{subject}_core_sheet", site="placeholder.com", mongo_client=mongo_client, db_name=db_name, **kwargs)
    class LeetCodeSQLHandler(SheetHandler): pass
    class GFGMustDoProductHandler(SheetHandler): pass
    class LeetCodeDSA75Handler(SheetHandler): pass
    class MicrosoftDSAHandler(SheetHandler): pass
    class PhonePeDSAHandler(SheetHandler): pass
    class OracleDSAHandler(SheetHandler): pass
    class LinuxCommandsHandler(SheetHandler): pass
    class DockerCommandsHandler(SheetHandler): pass
    class LanggraphHandler(SheetHandler): pass
    class DSACommonPatterns(SheetHandler): pass
# --- End Placeholder Imports ---


class SheetHandlerFactory:
    """Factory to create SheetHandler objects."""

    @staticmethod
    def create_handler(
        sheet_type: str,
        mongo_client: MongoClient, # Added MongoClient parameter
        db_name: str               # Added Database name parameter
    ) -> SheetHandler:
        """
        Creates and returns the appropriate SheetHandler instance.

        Args:
            sheet_type (str): The identifier for the sheet type (e.g., "sde_sheet").
            mongo_client (MongoClient): The active MongoDB client instance.
            db_name (str): The name of the MongoDB database.

        Returns:
            SheetHandler: An instance of the corresponding SheetHandler subclass.

        Raises:
            ValueError: If the sheet_type is not recognized.
        """
        if sheet_type == "sde_sheet":
            # Pass mongo_client and db_name to the constructor
            return SDESheetHandler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type in ["dbms_core_sheet", "os_core_sheet", "cn_core_sheet"]:
            subject = sheet_type.split("_")[0]
            # Pass subject, mongo_client, and db_name to the constructor
            return CoreSheetHandler(subject=subject, mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "lc_sql_50":
            # Pass mongo_client and db_name to the constructor
            return LeetCodeSQLHandler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "must_do_product_gfg":
            # Pass mongo_client and db_name to the constructor
            return GFGMustDoProductHandler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "lc_dsa_75":
            # Pass mongo_client and db_name to the constructor
            return LeetCodeDSA75Handler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "microsoft_dsa":
            # Pass mongo_client and db_name to the constructor
            return MicrosoftDSAHandler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "phonepe_dsa":
            # Pass mongo_client and db_name to the constructor
            return PhonePeDSAHandler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "oracle_dsa":
            # Pass mongo_client and db_name to the constructor
            return OracleDSAHandler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "linux_commands":
            # Pass mongo_client and db_name to the constructor
            return LinuxCommandsHandler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "docker_commands":
            # Pass mongo_client and db_name to the constructor
            return DockerCommandsHandler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "langgraph":
             # Pass mongo_client and db_name to the constructor
             return LanggraphHandler(mongo_client=mongo_client, db_name=db_name)

        elif sheet_type == "dsa_common_patterns":
             # Pass mongo_client and db_name to the constructor
             return DSACommonPatterns(mongo_client=mongo_client, db_name=db_name)

        else:
            # If sheet_type doesn't match any known handler
            raise ValueError(f"Invalid sheet type provided: {sheet_type}")

    @staticmethod
    def get_sheet_type(sheet_types: List[str]) -> List[str]:
        """
        Prompts the user to select sheet types.
        (This method is independent of handler creation logic).
        """
        # Ensure sheet_types is a list, provide default if necessary
        if not isinstance(sheet_types, list):
             print("Warning: sheet_types provided to get_sheet_type was not a list.")
             return [] # Or handle appropriately

        # Display options to the user
        print("\nAvailable sheet types:")
        for i, sheet in enumerate(sheet_types):
            print(f"  {i}: {sheet}")
        print("  Enter 'random' to process all.")
        print("  Enter a number to select one.")
        print("  Enter text to filter by name.")

        inp = input("Enter sheet type selection: ").strip()

        if inp.lower() == "random":
            return sheet_types # Return all available types
        elif inp.isdigit():
            try:
                index = int(inp)
                if 0 <= index < len(sheet_types):
                    return [sheet_types[index]] # Return list with the selected type
                else:
                    print(f"Invalid index: {index}. Please enter a number between 0 and {len(sheet_types) - 1}.")
                    return [] # Return empty list for invalid index
            except ValueError: # Should not happen due to isdigit, but safe practice
                 print("Invalid numeric input.")
                 return []
        elif inp: # If input is non-empty text (and not 'random' or a digit)
            # Filter sheets where the input text is a substring of the sheet type name
            filtered_sheets = [sheet for sheet in sheet_types if inp.lower() in sheet.lower()]
            if not filtered_sheets:
                 print(f"No sheet types found containing '{inp}'.")
                 return []
            return filtered_sheets
        else: # Handle empty input
             print("No input provided.")
             return []

