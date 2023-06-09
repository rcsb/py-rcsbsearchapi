"""Update the distribution json files; for developer use only"""
import json
from pathlib import Path

try:
    from .schema import _download_json_schema
except Exception:
    # ignore errors that may occur parsing the schema
    pass

if __name__ == "__main__":
    path = Path(__file__).parent.joinpath("resources", "metadata_schema.json")
    print(path)
    with open(path, "wt", encoding="utf-8") as file:
        latest = _download_json_schema()
        json.dump(latest, file)
