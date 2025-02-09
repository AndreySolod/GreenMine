from app import sanitizer
from typing import Optional
from xml.etree.ElementTree import Element as etreeElement

class NmapScriptProcessor:
    script_processors = {}
        
    def __init_subclass__(cls):
        NmapScriptProcessor.script_processors[cls.script_id] = cls
    
    def process(self, script_element: etreeElement) -> Optional[str]:
        ''' Process the script with name and data. Returned True if processed and False otherwise '''
        script_id = script_element.get('id')
        if script_id in self.script_processors:
            return self.script_processors[script_id.strip()](script_element)
        return f'\n<h5>Script data:</h5>\n<h6>{script_id}</h6><p>{sanitizer.escape(script_element.get('output')).replace('\n', '<br />')}</p>'


class NmapScriptNbnsInterfaces(NmapScriptProcessor):
    script_id = 'nbns-interfaces'
    def __call__(self, script_element: etreeElement):
        pass