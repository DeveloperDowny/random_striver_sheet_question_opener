import json
import random

should_allow_repeats = False

file_path = "data/sde_sheet.json"
history_file_path = "history/sde_sheet.json"



def main(data, history):

    random_step = random.choice(data["sheetData"])
    random_topic = random.choice(random_step["topics"])
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


