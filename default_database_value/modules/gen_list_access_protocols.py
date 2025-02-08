from pathlib import Path


class NetworkError(Exception):
    def __init__(self, text):
        self.txt = text


class ImportDefaultData:
    def __init__(self):
        self.is_complex = False

    def data(self, app, cls, db):
        with open(Path(__file__).parent / "nmap-services.txt") as f:
            self.nmap_port_file = f.read()
        port_strings = self.nmap_port_file.split('\n')
        slugs = []
        for ps in port_strings:
            if ps.startswith('#'):
                continue
            spl = ps.split('\t')
            if spl[0] == 'unknown' or len(spl) <= 1 or spl[1].split('/')[1] not in ['tcp', 'udp']:
                continue
            slug = spl[0].replace(" ", '-').replace(".", '-')
            if slug in slugs:
                continue
            np = cls()
            np.title = spl[0]
            np.string_slug = slug
            np.comment = " ".join(spl[3::])
            slugs.append(slug)
            db.session.add(np)
        db.session.commit()
