import csv
from pathlib import Path
from typing import Dict, Any


class ImportDefaultData:
    def __init__(self):
        self.is_complex = False
    
    def data(self, app, cls, db, GLOBAL_UPDATED_OBJECT_DICT: Dict[Any, Dict[str, Any]]):
        file_vendors = Path(__file__).parent / "mac-vendors-export.csv"
        app.logger.info("open file: " + str(file_vendors))
        with open(file_vendors, 'r') as f:
            reader = csv.DictReader(f, delimiter=',')
            for line in reader:
                mvd = cls()
                mvd.title = line["Vendor Name"]
                mvd.mac_prefix = line["Mac Prefix"].lower()
                mvd.is_private = line["Private"] != 'false'
                mvd.block_type = line["Block Type"]
                db.session.add(mvd)
            db.session.commit()
