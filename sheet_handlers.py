from sheet_handler import SheetHandler
import logging
from typing import List, Dict, Any
import enum

logger = logging.getLogger()


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


class DSACommonPatterns(SheetHandler):
    def __init__(self):
        super().__init__("dsa_common_patterns", "naukri.com")

    def get_title(self, topic: Dict[str, Any]) -> str:
        return topic["id"]

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return data["data"]
