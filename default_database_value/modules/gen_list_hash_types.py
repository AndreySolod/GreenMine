import json
from pathlib import Path
from typing import Dict, Any


class ImportDefaultData:
    def __init__(self):
        self.is_complex = True

    def data(self, app, cls, db, GLOBAL_UPDATED_OBJECT_DICT: Dict[Any, Dict[str, Any]]):
        with open(Path(__file__).parent / "hash_prototypes.json", 'r', encoding="utf8") as f:
            hashes_data = f.read().strip()
        hashes = json.loads(hashes_data)
        with open(Path(__file__).parent / "hash_common.json", 'r', encoding="utf8") as f:
            common_data = f.read().strip()
        populars = json.loads(common_data)
        hashinfo_list = []
        for p in hashes:
            for m in p['modes']:
                ht = cls()
                ht.title = m['name']
                ht.string_slug = m['name'].replace(' ', '-').replace('.', '-').replace('$', '-')
                ht.hashcat_mode = m['hashcat']
                ht.john_mode = m['john']
                ht.extended = m['extended']
                ht.is_popular = m['name'] in populars
                ht._regex = [p['regex']]
                collision = False
                for i in hashinfo_list:
                    if i.string_slug == ht.string_slug:
                        collision = True
                        i._regex.append(p['regex'])
                if not collision:
                    hashinfo_list.append(ht)
                    db.session.add(ht)
        self.hashinfo_list = hashinfo_list
        db.session.commit()

    def complex_data(self, app, db, models, GLOBAL_UPDATED_OBJECT_DICT: Dict[Any, Dict[str, Any]]):
        for ht in self.hashinfo_list:
            for regex in ht._regex:
                ht.regexs.add(db.session.scalars(db.select(models.HashPrototype).where(models.HashPrototype.regex==regex)).one())
            db.session.add(ht)
        db.session.commit()
