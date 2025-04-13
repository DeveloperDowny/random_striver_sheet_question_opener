from abc import ABC, abstractmethod
from typing import List, Dict, Any
import json
import logging
import os
import random
import urllib.parse
from config import Config

logger = logging.getLogger()


class SheetHandler(ABC):
    def __init__(self, file_name: str, site: str, jsons_path=None, difficulty=None):
        self.file_name = file_name
        self.site = site
        self.jsons_path = jsons_path
        self.difficulty = difficulty

        self.data_file_path = f"data/{file_name}.json"
        self.history_file_path = f"history/{file_name}.json"
        self.revision_file_path = f"revision/{file_name}.txt"

        # making the file reference absolute
        # self.base_dir = r"D:\DPythonProjects\random_striver_sheet_question_opener"
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file_path = os.path.join(self.base_dir, self.data_file_path)
        self.history_file_path = os.path.join(self.base_dir, self.history_file_path)
        self.revision_file_path = os.path.join(self.base_dir, self.revision_file_path)

        self.should_allow_repeats = False

    @abstractmethod
    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass

    def get_all_jsons(self):
        files = os.listdir(self.jsons_path)
        return files

    def pick_random_json(self):
        files = self.get_all_jsons()
        file = random.choice(files)
        return file

    def get_json(self, file):
        with open(f"{self.jsons_path}/{file}", "r") as f:
            data = json.load(f)
        return data

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


    def remove_solved(
        self, sheet_data: List[Dict[str, Any]], solved_ids: List[str]
    ) -> List[Dict[str, Any]]:
        logger.debug("Removing solved items from sheet data.")
        solved_set = set(solved_ids)
        return [item for item in sheet_data if item["id"] not in solved_set]

    def get_random_topic(self, filtered_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        return random.choice(filtered_data)

    def create_link(self, title: str) -> str:
        url_safe_title = urllib.parse.quote_plus(title)
        return f"https://www.google.com/search?q={url_safe_title}+site%3A{self.site}"

    def update_history(self, history: List[str], new_id: str) -> None:
        if Config.kDebugMode:
            logger.info("Debug mode enabled. Skipping history update.")
            return
        history.append(new_id)
        with open(self.history_file_path, "w") as file:
            json.dump({"solved_ids": history}, file, indent=2)
        logger.info("History updated.")

    def get_title(self, topic: Dict[str, Any]) -> str:
        return topic["title"]

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
        link = self.create_link(self.get_title(random_topic))
        logger.info(f"Link: {link}")
        self.update_history(history, id)

        should_mark_for_revison = input("Mark for revision? (y/n): ")
        if should_mark_for_revison.lower() == "y":
            self.mark_revision(history)

    # if marked as revision, delete the last entry from history
    def mark_revision(self, history: List[str]) -> None:
        if Config.kDebugMode:
            logger.info("Debug mode enabled. Skipping history update.")
            return
        revision_id = history.pop()
        revision_id = str(revision_id)
        with open(self.revision_file_path, "a") as file:
            file.write(revision_id + "\n")

        with open(self.history_file_path, "w") as file:
            json.dump({"solved_ids": history}, file, indent=2)
        logger.info("History updated.")
