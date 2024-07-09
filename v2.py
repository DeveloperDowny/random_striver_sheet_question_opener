import json
import random
import logging
import urllib.parse
from abc import ABC, abstractmethod
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("debug.log"),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger()
kdebugMode = False

class SheetHandler(ABC):
    def __init__(self, file_name: str, site: str):
        self.file_name = file_name
        self.site = site
        self.data_file_path = f"data/{file_name}.json"
        self.history_file_path = f"history/{file_name}.json"
        self.should_allow_repeats = False

    @abstractmethod
    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass

    def remove_solved(self, sheet_data: List[Dict[str, Any]], solved_ids: List[str]) -> List[Dict[str, Any]]:
        logger.debug("Removing solved items from sheet data.")
        solved_set = set(solved_ids)
        return [item for item in sheet_data if item['id'] not in solved_set]

    def get_random_topic(self, filtered_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        return random.choice(filtered_data)

    def create_link(self, title: str) -> str:
        url_safe_title = urllib.parse.quote_plus(title)
        return f"https://www.google.com/search?q={url_safe_title}+site%3A{self.site}"

    def update_history(self, history: List[str], new_id: str) -> None:
        if kdebugMode:
            logger.info("Debug mode enabled. Skipping history update.")
            return
        history.append(new_id)
        with open(self.history_file_path, "w") as file:
            json.dump({"solved_ids": history}, file, indent=2)
        logger.info("History updated.")

    def process(self) -> None:
        logger.info(f"Processing {self.file_name}")
        with open(self.data_file_path, "r") as file:
            data = json.load(file)
        with open(self.history_file_path, "r") as file:
            history = json.load(file)["solved_ids"]

        flattened = self.flatten(data)
        filtered_data = self.remove_solved(flattened, history)
        random_topic = self.get_random_topic(filtered_data)
        id = random_topic["id"]

        if id in history and not self.should_allow_repeats:
            logger.info("Repeat found, reprocessing.")
            self.process()
            return

        logger.info(f"Selected topic: {json.dumps(random_topic, indent=2)}")
        link = self.create_link(random_topic["title"])
        logger.info(f"Link: {link}")
        self.update_history(history, id)

class SDESheetHandler(SheetHandler):
    def __init__(self):
        super().__init__("sde_sheet", "naukri.com")

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug("Flattening SDE sheet data.")
        return [item for sublist in data["sheetData"] for item in sublist["topics"]]

class CoreSheetHandler(SheetHandler):
    def __init__(self, subject: str):
        super().__init__(f"{subject}_core_sheet", "geeksforgeeks.org")

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug("Flattening core sheet data.")
        return [item for sublist in data["sheetData"] for item in sublist["data"]]

class LeetCodeSQLHandler(SheetHandler):
    def __init__(self):
        super().__init__("lc_sql_50", "leetcode.com")

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug("Flattening LC SQL 50 data.")
        flattened_list = [item for sublist in data["sheetData"] for item in sublist["questions"]]
        logger.info(f"Total questions: {len(flattened_list)}")
        return flattened_list

class SheetHandlerFactory:
    @staticmethod
    def create_handler(sheet_type: str) -> SheetHandler:
        if sheet_type == "sde_sheet":
            return SDESheetHandler()
        elif sheet_type in ["dbms_core_sheet", "os_core_sheet", "cn_core_sheet"]:
            subject = sheet_type.split("_")[0]
            return CoreSheetHandler(subject)
        elif sheet_type == "lc_sql_50":
            return LeetCodeSQLHandler()
        else:
            raise ValueError(f"Invalid sheet type: {sheet_type}")
    
    @staticmethod
    def get_sheet_type(sheet_types) -> List[str]:
        inp = input("Enter sheet type: ")
        if inp.isdigit():
            return [sheet_types[int(inp)]]
        elif inp.isalpha():
            return [sheet for sheet in sheet_types if inp in sheet]
        else:
            raise ValueError("Invalid input.")

def main():
    logger.info("Script started.")
    sheet_types = ["sde_sheet", "dbms_core_sheet", "os_core_sheet", "cn_core_sheet", "lc_sql_50"]
    filtered_sheet_types = SheetHandlerFactory.get_sheet_type(sheet_types)
    sheet_type = random.choice(filtered_sheet_types)
    handler = SheetHandlerFactory.create_handler(sheet_type)
    handler.process()
    logger.info("Script finished.")

if __name__ == "__main__":
    main()