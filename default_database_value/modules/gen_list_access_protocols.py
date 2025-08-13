from pathlib import Path
from typing import Dict, Any
import os


class NetworkError(Exception):
    def __init__(self, text):
        self.txt = text


class ImportDefaultData:
    def __init__(self):
        self.is_complex = False

    def data(self, app, cls, db, GLOBAL_UPDATED_OBJECT_DICT: Dict[Any, Dict[str, Any]]):
        with open(Path(__file__).parent / "nmap-services.txt") as f:
            self.nmap_port_file = f.read()
        port_strings = self.nmap_port_file.split('\n')
        slugs = []
        template_path = Path(__file__).parent / "access_protocols_parameter_templates"
        script_path = Path(__file__).parent / "access_protocol_script_templates"
        if cls not in GLOBAL_UPDATED_OBJECT_DICT:
            GLOBAL_UPDATED_OBJECT_DICT[cls] = {}
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
            # access protocol templates
            if os.path.exists(template_path / (np.title + ".html")):
                with open(template_path / (np.title + ".html"), 'r') as f:
                    np.additional_attributes_template = f.read()
            if os.path.exists(script_path / (np.title + ".js")):
                with open(script_path / (np.title + ".js"), 'r') as f:
                    np.additional_attributes_script = f.read()
            slugs.append(slug)
            GLOBAL_UPDATED_OBJECT_DICT[cls][slug] = np
