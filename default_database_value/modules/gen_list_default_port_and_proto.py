from pathlib import Path
import logging
import sqlalchemy as sa
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
from typing import Dict, Any

class NetworkError(Exception):
    def __init__(self, text):
        self.txt = text


class ImportDefaultData:
    def __init__(self):
        self.is_complex = True

    def data(self, app, cls, db, GLOBAL_UPDATED_OBJECT_DICT: Dict[Any, Dict[str, Any]]):
        with open(Path(__file__).parent / "nmap-services.txt") as f:
            self.nmap_port_file = f.read()
        port_strings = self.nmap_port_file.split('\n')
        self.list_default_proto = []
        if cls not in GLOBAL_UPDATED_OBJECT_DICT:
            GLOBAL_UPDATED_OBJECT_DICT[cls] = {}
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
            GLOBAL_UPDATED_OBJECT_DICT[cls][f'{ndp.port}-{ndp._transport_level_protocol_string_slug}-{ndp._access_protocol_string_slug}'] = ndp

    def complex_data(self, app, db, models, GLOBAL_UPDATED_OBJECT_DICT: Dict[Any, Dict[str, Any]]):
        progress = -1
        for port in self.list_default_proto:
            if port.port // 10000 > progress:
                logger.info(f'Current protocol: {port.port}')  # logging
                progress = port.port // 10000
            transport_level_protocol = db.session.scalars(sa.select(models.ServiceTransportLevelProtocol).where(models.ServiceTransportLevelProtocol.string_slug==port._transport_level_protocol_string_slug)).first()
            if transport_level_protocol is None and models.ServiceTransportLevelProtocol in GLOBAL_UPDATED_OBJECT_DICT and port._transport_level_protocol_string_slug in GLOBAL_UPDATED_OBJECT_DICT[models.ServiceTransportLevelProtocol]:
                transport_level_protocol = GLOBAL_UPDATED_OBJECT_DICT[models.ServiceTransportLevelProtocol][port._transport_level_protocol_string_slug]
            elif transport_level_protocol is None:
                logger.error(f"Cannot find transport level protocol with slug {port._transport_level_protocol_string_slug}")
                raise ValueError(f"Cannot find transport level protocol with slug {port._transport_level_protocol_string_slug}")
            port.transport_level_protocol = transport_level_protocol
            access_protocol = db.session.scalars(sa.select(models.AccessProtocol).where(models.AccessProtocol.string_slug==port._access_protocol_string_slug)).first()
            if access_protocol is None and models.AccessProtocol in GLOBAL_UPDATED_OBJECT_DICT and port._access_protocol_string_slug in GLOBAL_UPDATED_OBJECT_DICT[models.AccessProtocol]:
                access_protocol = GLOBAL_UPDATED_OBJECT_DICT[models.AccessProtocol][port._access_protocol_string_slug]
            elif access_protocol is None:
                logger.error(f"Cannot find access protocol with slug {port._access_protocol_string_slug}")
                raise ValueError(f"Cannot find access protocol with slug {port._access_protocol_string_slug}")
            port.access_protocol = access_protocol