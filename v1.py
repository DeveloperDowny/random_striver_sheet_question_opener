import json
import random
import logging
# encode url
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("debug.log"),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger()

should_allow_repeats = False

# sde_sheet | dbms_core_sheet
to_study_options = ["sde_sheet", "dbms_core_sheet", "os_core_sheet", "cn_core_sheet", "lc_sql_50", "phonepe_dsa"]
corresponding_site_list = ["naukri", "geeksforgeeks", "geeksforgeeks", "geeksforgeeks", "leetcode", "naukri"]
knda = False
if knda:
    ind = random.randint(1, len(to_study_options)-1)
    logger.info(f"Randomly selected: {to_study_options[ind]}")
else:
    ind = 0
ind = 4
to_study = to_study_options[ind]

file_path = f"data/{to_study}.json"
history_file_path = f"history/{to_study}.json"

def remove_solved(sheet_data, solved_ids):
    logger.debug("Removing solved items from sheet data.")
    solved_set = set(solved_ids)
    return [item for item in sheet_data if item['id'] not in solved_set]

def sde_flattener(data):
    logger.debug("Flattening SDE sheet data.")
    return [item for sublist in data["sheetData"] for item in sublist["topics"]]

def core_flattener(data):
    logger.debug("Flattening core sheet data.")
    return [item for sublist in data["sheetData"] for item in sublist["data"]]

def lc_sql_50_flattener(data):
    logger.debug("Flattening LC SQL 50 data.")
    flattened_list =  [item for sublist in data["sheetData"] for item in sublist["questions"]]
    logger.info(f"Total questions: {len(flattened_list)}")
    return flattened_list

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

def main(data, history):
    logger.info("Starting main function.")
    flattened = flatten(data)
    filtered_data = remove_solved(flattened, history)
    random_topic = random.choice(filtered_data)
    id = random_topic["id"]

    if id in history:
        if not should_allow_repeats:
            logger.info("Repeat found, rerunning main with updated history.")
            main(data, history)
            return
    logger.info(f"Selected topic: {json.dumps(random_topic, indent=2)}")
    # custom link 
    title = random_topic["title"]
    # google search link with the title and the file_name
    url_safe_title = urllib.parse.quote_plus(title)
    site = corresponding_site_list[ind]
    link = f"https://www.google.com/search?q={url_safe_title}+site%3A{site}.com"
    logger.info(f"Link: {link}")
    history.append(id)
    with open(history_file_path, "w") as file:
        new_history = {
            "solved_ids": history
        }
        json.dump(new_history, file, indent=2)
    logger.info("History updated.")

if __name__ == "__main__":
    logger.info("Script started.")
    with open(file_path, "r") as file:
        data = json.load(file)
    with open(history_file_path, "r") as file:
        history = json.load(file)
    main(data, history["solved_ids"])
    logger.info("Script finished.")
    
    
#  Ideas. create a util picker based on condition
# The util will be base class
# The specialised will be cn_core_sheet, os_core_sheet, dbms_core_sheet, sde_sheet, lc_sql_50
# The specialised will have a method to flatten the data
# The specialised will have a method to remove solved
# The specialised will have a method to pick random
# The specialised will have a method to update history
# The specialised will have a method to log

# Do object oriented programming from now on