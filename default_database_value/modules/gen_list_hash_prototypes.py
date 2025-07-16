import json
from pathlib import Path
from typing import Dict, Any


class ImportDefaultData:
    def __init__(self):
        self.is_complex = False

    def data(self, app, cls, db, GLOBAL_UPDATED_OBJECT_DICT: Dict[Any, Dict[str, Any]]):
        with open(Path(__file__).parent / "hash_prototypes.json", 'r', encoding="utf8") as f:
            hashes_data = f.read().strip()
        hashes = json.loads(hashes_data)
        for p in hashes:
            hp = cls(regex=p["regex"])
            db.session.add(hp)
        db.session.commit()
