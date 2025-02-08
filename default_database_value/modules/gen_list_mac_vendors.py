import csv
import os


class ImportDefaultData:
    def __init__(self):
        self.is_complex = False
    
    def data(self, app, cls, db):
        file_vendors = os.path.join(os.path.dirname(__file__), "mac-vendors-export.csv")
        app.logger.info("open file: " + file_vendors)
        with open(file_vendors, 'r') as f:
            reader = csv.DictReader(f, delimiter=',')
            for line in reader:
                mvd = cls()
                mvd.title = line["Vendor Name"]
                mvd.mac_prefix = line["Mac Prefix"].lower()
                mvd.is_private = line["Private"] == 'false'
                mvd.block_type = line["Block Type"]
                db.session.add(mvd)
            db.session.commit()
