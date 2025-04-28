# -*- coding: utf-8 -*-
"""
Main script to select and process a sheet using SheetHandlers connected to MongoDB.
"""

import random
import logging
import sys # Import sys for exiting
from db_config import DBConfig

# Assuming SheetHandlerFactory is in sheet_handler_factory.py
# Ensure this import points to the updated factory file
try:
    from sheet_handler_factory import SheetHandlerFactory
except ImportError:
     print("Fatal Error: Could not import SheetHandlerFactory. Make sure sheet_handler_factory_mongo.py is accessible.")
     sys.exit(1) # Exit if the factory cannot be imported

# Import MongoClient
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
except ImportError:
     print("Fatal Error: Could not import pymongo. Please install it: pip install pymongo")
     sys.exit(1)

# --- Configuration ---
db_config = DBConfig(_env_file=r"D:\DPythonProjects\roulette\.env")

# Configure logging (moved setup to main execution block)
logger = logging.getLogger(__name__) # Use __name__

# --- Main Function ---

def main():
    """
    Main execution function:
    1. Connects to MongoDB.
    2. Gets user sheet selection.
    3. Creates the appropriate handler via the factory.
    4. Processes the selected sheet using the handler.
    5. Closes the MongoDB connection.
    """
    logger.info("Script started.")

    # 1. Connect to MongoDB
    mongo_client: MongoClient = None # Initialize to None
    try:
        mongo_client = MongoClient(db_config.MONGODB_URI)
        # Validate connection
        mongo_client.admin.command('ismaster')
        logger.info(f"Successfully connected to MongoDB. Using database: '{db_config.DATABASE_NAME}'")
    except ConnectionFailure:
        logger.exception(f"Fatal Error: Failed to connect to MongoDB at {db_config.MONGODB_URI}")
        return # Exit main if connection fails
    except Exception as e:
        logger.exception(f"Fatal Error: An unexpected error occurred during MongoDB connection: {e}")
        return # Exit main

    # 2. Get sheet type selection
    sheet_types = [
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
    filtered_sheet_types = SheetHandlerFactory.get_sheet_type(sheet_types)

    # Handle empty selection
    if not filtered_sheet_types:
         logger.warning("No sheet types selected or found based on input. Exiting.")
         if mongo_client:
             mongo_client.close()
             logger.info("MongoDB connection closed.")
         return # Exit main

    # 3. Choose a random sheet and create handler
    try:
        sheet_type = random.choice(filtered_sheet_types)
        logger.info(f"Selected sheet type: {sheet_type}")

        # Create handler using the factory, passing the client and db name
        handler = SheetHandlerFactory.create_handler(
            sheet_type=sheet_type,
            mongo_client=mongo_client,
            db_name=db_config.DATABASE_NAME
        )

        # 4. Process using the handler
        handler.process()

    except IndexError:
         # Should not happen due to the check above, but as a safeguard
         logger.error("Error: Cannot choose from an empty list of sheet types.")
    except ValueError as ve:
         # Catch errors from create_handler (e.g., invalid sheet_type)
         logger.error(f"Error creating handler: {ve}")
    except Exception as e:
         # Catch unexpected errors during handler creation or processing
         logger.exception(f"An unexpected error occurred: {e}")

    # 5. Close MongoDB connection
    finally:
        if mongo_client:
            mongo_client.close()
            logger.info("MongoDB connection closed.")

    logger.info("Script finished.")


# --- Script Execution ---

if __name__ == "__main__":
    # Configure logging (moved here from global scope)
    logging.basicConfig(
        level=logging.INFO, # Set desired logging level (e.g., INFO, DEBUG)
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", # Include logger name
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler("debug.log", mode='a'), # Append to log file
            logging.StreamHandler(sys.stdout) # Log to console
        ]
    )
    main()
