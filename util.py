import json
from pathlib import Path


def store_json(folder, id, data):
    with open(Path(__file__).parent.resolve() / folder / f"{id}.json", "w") as f:
        if type(data) is dict:
            json.dump(data, f)
        else:
            f.write(data)
