import json
import random

 

file_path = "data/sde_sheet.json"
with open(file_path, "r") as file:
    data = json.load(file)
random_step = random.choice(data["sheetData"])
random_topic = random.choice(random_step["topics"])
print(json.dumps(random_topic, indent=2))


