class NmapScriptProcessor:
    script_processors = {}
    def __init__(self, script_name: str, script_data: dict):
        return 
    
    def __init_subclass__(cls):
        NmapScriptProcessor.script_processors[cls.name] = cls
    
    def process(self, script_name: str, script_data: dict):
        if script_name in self.script_processors:
            self.script_processors[script_name](script_data)