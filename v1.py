import json
import random

should_allow_repeats = False

# sde_sheet | dbms_core_sheet
to_study_options = ["sde_sheet", "dbms_core_sheet", "os_core_sheet", "cn_core_sheet"] 
to_study = to_study_options[3]

file_path = f"data/{to_study}.json"
history_file_path = f"history/{to_study}.json"



def remove_solved(sheet_data, solved_ids):
    solved_set = set(solved_ids)
    return [item for item in sheet_data if item['id'] not in solved_set]

def sde_flattener(data):
    return [item for sublist in data["sheetData"] for item in sublist["topics"]]

def core_flattener(data):
    return [item for sublist in data["sheetData"] for item in sublist["data"]]
    

def flatten(data):
    if to_study == "sde_sheet":
        return sde_flattener(data)
    elif "core_sheet" in to_study: 
        return core_flattener(data)
    else:
        raise ValueError("Invalid value for to_study")
    
    # return [item for sublist in data["sheetData"] for item in sublist["topics"]]
def main(data, history):
    # flattened = [item for sublist in data["sheetData"] for item in sublist["topics"]]
    flattened = flatten(data)
    filtered_data = remove_solved(flattened, history)
    # random_step = random.choice(data["sheetData"])
    # random_step = random.choice(filtered_data)
    # random_topic = random.choice(random_step["topics"])
    random_topic = random.choice(filtered_data)
    id = random_topic["id"]

    if id in history:
        if not should_allow_repeats:
            main(data, history)
            return 
    print(json.dumps(random_topic, indent=2))
    # add to history and save
    history.append(id)
    with open(history_file_path, "w") as file:
        new_history = {
            "solved_ids": history
        }
        json.dump(new_history, file, indent=2)

if __name__ == "__main__":
    with open(file_path, "r") as file:
        data = json.load(file)
    with open(history_file_path, "r") as file:
        history = json.load(file)
    main(data,history["solved_ids"]) 


