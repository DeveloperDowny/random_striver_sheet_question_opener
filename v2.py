import json
import random
import logging
import urllib.parse
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
import enum


logger = logging.getLogger()
kdebugMode = False


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
        random_json_file = self.pick_random_json()
        data = self.get_json(random_json_file)
        logger.debug(f"Flattening {self.file_name} data.")
        questions = data["data"]["problem_list"]
        questions = [
            item for item in questions if item["difficulty"] == self.difficulty.value
        ]
        return questions

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
        if kdebugMode:
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
        if kdebugMode:
            logger.info("Debug mode enabled. Skipping history update.")
            return
        revision_id = history.pop()
        revision_id = str(revision_id)
        with open(self.revision_file_path, "a") as file:
            file.write(revision_id + "\n")

        with open(self.history_file_path, "w") as file:
            json.dump({"solved_ids": history}, file, indent=2)
        logger.info("History updated.")


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
        flattened_list = [
            item for sublist in data["sheetData"] for item in sublist["questions"]
        ]
        return flattened_list


# leetcodedsa75handler
class LeetCodeDSA75Handler(SheetHandler):
    def __init__(self):
        super().__init__("lc_dsa_75", "leetcode.com")

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug("Flattening LC DSA 75 data.")
        flattened_list = [
            item for sublist in data["sheetData"] for item in sublist["questions"]
        ]
        return flattened_list


class GFGMustDoProductHandler(SheetHandler):
    def __init__(self):
        super().__init__("must_do_product_gfg", "geeksforgeeks.org")

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug("Flattening GFG must do product data.")
        return data["sheetData"]

    # def create_link(self, link: str) -> str:
    #     return link


class NaukriDifficulties(enum.Enum):
    EASY = "Easy"
    MEDIUM = "Moderate"
    HARD = "Hard"


class MicrosoftDSAHandler(SheetHandler):
    def __init__(self):
        super().__init__(
            "microsoft_dsa",
            "naukri.com",
            "microsoft_question_jsons",
            NaukriDifficulties.MEDIUM,
        )
        self.difficulty = NaukriDifficulties.MEDIUM  # default difficulty

    def get_title(self, topic: Dict[str, Any]) -> str:
        return topic["name"]

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.questions_from_jsons(data)
    
class PhonePeDSAHandler(SheetHandler):
    def __init__(self):
        super().__init__(
            "phonepe_dsa",
            "naukri.com",
            "phonepe_question_jsons",
            NaukriDifficulties.MEDIUM,
        )
        self.difficulty = NaukriDifficulties.MEDIUM  # default difficulty

    def get_title(self, topic: Dict[str, Any]) -> str:
        return topic["name"]

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.questions_from_jsons(data)
    
class PhonePeDSAHandler(SheetHandler):
    def __init__(self):
        super().__init__(
            "phonepe_dsa",
            "naukri.com",
            "phonepe_question_jsons",
            NaukriDifficulties.MEDIUM,
        )
        self.difficulty = NaukriDifficulties.MEDIUM  # default difficulty

    def get_title(self, topic: Dict[str, Any]) -> str:
        return topic["name"]

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.questions_from_jsons(data)


class OracleDSAHandler(SheetHandler):
    def __init__(self):
        super().__init__(
            "oracle_dsa",
            "leetcode.com",
            "oracle_question_jsons",
            NaukriDifficulties.MEDIUM,
        )
        self.difficulty = NaukriDifficulties.MEDIUM  # default difficulty

    def get_title(self, topic: Dict[str, Any]) -> str:
        return topic["name"]

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.questions_from_jsons(data)


class LinuxCommandsHandler(SheetHandler):
    def __init__(self):
        super().__init__("linux_commands", "manpages.ubuntu.com")

    def get_title(self, topic: Dict[str, Any]) -> str:
        return topic["id"]

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return data["data"]


class DockerCommandsHandler(SheetHandler):
    def __init__(self):
        super().__init__("docker_commands", "docs.docker.com")

    def get_title(self, topic: Dict[str, Any]) -> str:
        return topic["id"] + " command"

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return data["data"]


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
        elif sheet_type == "must_do_product_gfg":
            return GFGMustDoProductHandler()
        elif sheet_type == "lc_dsa_75":
            return LeetCodeDSA75Handler()
        elif sheet_type == "microsoft_dsa":
            return MicrosoftDSAHandler()
        elif sheet_type == "phonepe_dsa":
            return PhonePeDSAHandler()
        elif sheet_type == "oracle_dsa":
            return OracleDSAHandler()
        elif sheet_type == "linux_commands":
            return LinuxCommandsHandler()
        elif sheet_type == "docker_commands":
            return DockerCommandsHandler()
        else:
            raise ValueError(f"Invalid sheet type: {sheet_type}")

    @staticmethod
    def get_sheet_type(sheet_types) -> List[str]:
        inp = input("Enter sheet type: ")
        if inp == "random":
            return sheet_types
        if inp.isdigit():
            return [sheet_types[int(inp)]]
        else:
            return [sheet for sheet in sheet_types if inp in sheet]


def main():
    logger.info("Script started.")
    sheet_types = [
        "sde_sheet",
        "dbms_core_sheet",
        "os_core_sheet",
        "cn_core_sheet",
        "lc_sql_50",
        "must_do_product_gfg",
        "lc_dsa_75",
        "microsoft_dsa",
        "oracle_dsa",
        "linux_commands",
        "docker_commands",
    ]
    filtered_sheet_types = SheetHandlerFactory.get_sheet_type(sheet_types)
    sheet_type = random.choice(filtered_sheet_types)
    handler = SheetHandlerFactory.create_handler(sheet_type)
    handler.process()

    logger.info("Script finished.")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("debug.log"), logging.StreamHandler()],
    )
    main()
