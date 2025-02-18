import re
from app import db
import app.models as models
from typing import List, Dict, Optional
import sqlalchemy as sa


class NameThatHash:
    def __init__(self):
        self.prototypes = db.session.scalars(sa.select(models.HashPrototype)).all()

    def identify(self, chash: str) -> List[models.HashType]:
        output = []
        chash = chash.strip()
        for proto in self.prototypes:
            regex = re.compile(proto.regex, re.IGNORECASE)
            if regex.match(chash):
                output += list(proto.hash_types)
        return output

    def identify_all(self, chash:str):
        output = []
        chash = chash.strip()
        for proto in self.prototypes:
            regex = re.compile(proto.regex, re.IGNORECASE)
            if regex.findall(chash):
                output += list(proto.hash_types)
        return output
