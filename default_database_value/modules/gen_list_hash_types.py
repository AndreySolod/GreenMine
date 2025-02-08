import requests
import json


class ImportDefaultData:
    def __init__(self):
        self.is_complex = True

    def data(self, app, cls, db):
        req = requests.get('https://raw.githubusercontent.com/noraj/haiti/master/data/prototypes.json').text
        hashes = json.loads(req)
        req = requests.get('https://raw.githubusercontent.com/noraj/haiti/master/data/commons.json').text
        populars = json.loads(req)
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

    def complex_data(self, app, db, models):
        for ht in self.hashinfo_list:
            for regex in ht._regex:
                ht.regexs.add(db.session.scalars(db.select(models.HashPrototype).where(models.HashPrototype.regex==regex)).one())
            db.session.add(ht)
        db.session.commit()
