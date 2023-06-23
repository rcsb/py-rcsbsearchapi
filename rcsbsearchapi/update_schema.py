"""Update the distribution json files; for developer use only
This is currently not in use. """
import json
from pathlib import Path

try:
    from .schema import _download_schema
except Exception:
    # ignore errors that may occur parsing the schema
    pass

if __name__ == "__main__":
    path = Path(__file__).parent.joinpath("resources", "metadata_schema.json")
    print(path)
    with open(path, "wt", encoding="utf-8") as file:
        latest = _download_schema("this will be replaced with the URL once this file is in use. ")
        json.dump(latest, file)
