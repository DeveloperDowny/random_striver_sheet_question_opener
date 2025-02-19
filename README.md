# Upgrade from v1 -> v2

- Took Object Oriented Approach
- Used Factory Design Pattern to create object of the required class dynamically
- This helps improved readability, maintainability and extensibility
- So in the v1.py, I wanted to have a simple addon, support LeetCode SQL 50 sheet too
- I found myself making changes to check what type of sheet I am working with everywhere like the following

```python
def flatten(data):
    logger.info(f"Flattening data for {to_study}.")
    if to_study == "sde_sheet":
        return sde_flattener(data)
    elif "core_sheet" in to_study:
        return core_flattener(data)
    elif to_study == "lc_sql_50":
        return lc_sql_50_flattener(data)
    else:
        logger.error("Invalid value for to_study")
        raise ValueError("Invalid value for to_study")
```

- There are multiple problems with this approach apart from the extensibility problem
- So, I decided to apply the [Factory Method](https://refactoring.guru/design-patterns/factory-method) Design Pattern and rewrite the code (now found in v2.py)
- Now, I have SheetHandler, an abstract base class (ABC)

```python
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
        return f"https://www.google.com/search?q={url_safe_title}+site%3A{self.site}.com"

    def update_history(self, history: List[str], new_id: str) -> None:
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
```

And the following subclasses of it

```python
class SDESheetHandler(SheetHandler):
    def __init__(self):
        super().__init__("sde_sheet", "naukri")

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug("Flattening SDE sheet data.")
        return [item for sublist in data["sheetData"] for item in sublist["topics"]]

class CoreSheetHandler(SheetHandler):
    def __init__(self, subject: str):
        super().__init__(f"{subject}_core_sheet", "geeksforgeeks")

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug("Flattening core sheet data.")
        return [item for sublist in data["sheetData"] for item in sublist["data"]]

class LeetCodeSQLHandler(SheetHandler):
    def __init__(self):
        super().__init__("lc_sql_50", "leetcode")

    def flatten(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.debug("Flattening LC SQL 50 data.")
        flattened_list = [item for sublist in data["sheetData"] for item in sublist["questions"]]
        logger.info(f"Total questions: {len(flattened_list)}")
        return flattened_list
```

The following SheetHandlerFactory class implements the Factory pattern. This pattern provides an interface for creating different derived class of the same base class. In this case, the factory creates different types of SheetHandler objects based on the input sheet type.

```python
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
```

Following is the entry point of the code

```python
def main():
    logger.info("Script started.")
    sheet_types = ["sde_sheet", "dbms_core_sheet", "os_core_sheet", "cn_core_sheet", "lc_sql_50"]
    sheet_type = random.choice(sheet_types)
    handler = SheetHandlerFactory.create_handler(sheet_type)
    handler.process()
    logger.info("Script finished.")
```
