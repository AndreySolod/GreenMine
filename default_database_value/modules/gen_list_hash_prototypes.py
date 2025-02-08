import requests
import json


class ImportDefaultData:
    def __init__(self):
        self.is_complex = False

    def data(self, app, cls, db):
        req = requests.get('https://raw.githubusercontent.com/noraj/haiti/master/data/prototypes.json').text
        hashes = json.loads(req)
        for p in hashes:
            hp = cls(regex=p["regex"])
            db.session.add(hp)
        db.session.commit()
