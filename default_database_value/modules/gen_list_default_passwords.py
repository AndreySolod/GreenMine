from app import sanitizer
from pathlib import Path
import csv


class ImportDefaultData:
    def __init__(self):
        self.is_complex = False
    
    def data(self, app, cls, db):
        file_default_creds = Path(__file__).parent / "DefaultCreds-Cheat-Sheet.csv"
        with open(file_default_creds, 'r') as f:
            reader = csv.DictReader(f, delimiter=",")
            for line in reader:
                cred = cls()
                cred.title = sanitizer.escape(line['productvendor'])
                cred.login = sanitizer.escape(line['username'])
                cred.password = sanitizer.escape(line['password'])
                db.session.add(cred)
        db.session.commit()