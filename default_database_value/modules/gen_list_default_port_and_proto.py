from pathlib import Path
import logging
import sqlalchemy as sa
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

class NetworkError(Exception):
    def __init__(self, text):
        self.txt = text


class ImportDefaultData:
    def __init__(self):
        self.is_complex = True

    def data(self, app, cls, db):
        with open(Path(__file__).parent / "nmap-services.txt") as f:
            self.nmap_port_file = f.read()
        port_strings = self.nmap_port_file.split('\n')
        self.list_default_proto = []
        for ps in port_strings:
            if ps.startswith('#'):
                continue
            spl = ps.split('\t')
            if spl[0] == 'unknown' or len(spl) <= 1 or spl[1].split('/')[1] not in ['tcp', 'udp']:
                continue
            ndp = cls()
            ndp.port = int(spl[1].split('/')[0])
            ndp._transport_level_protocol_string_slug = spl[1].split('/')[1]
            ndp._access_protocol_string_slug = spl[0].replace(" ", '-').replace(".", '-')
            self.list_default_proto.append(ndp)
            db.session.add(ndp)
        db.session.commit()

    def complex_data(self, app, db, models):
        progress = -1
        for port in self.list_default_proto:
            if port.port // 10000 > progress:
                logger.info(f'Current protocol: {port.port}')  # logging
                progress = port.port // 10000
            port.transport_level_protocol = db.session.scalars(sa.select(models.ServiceTransportLevelProtocol).where(models.ServiceTransportLevelProtocol.string_slug==port._transport_level_protocol_string_slug)).one()
            port.access_protocol = db.session.scalars(sa.select(models.AccessProtocol).where(models.AccessProtocol.string_slug==port._access_protocol_string_slug)).one()
            db.session.add(port)
        db.session.commit()
