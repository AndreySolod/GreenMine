from flask import Flask
from typing import Optional, List
import importlib
import pkgutil
from flask_babel import lazy_gettext as _l


class AutomationModules:
    ''' The class that implements the functionality of the application for Flask is used to simplify the initialization of the application '''
    _action_modules = []
    _sorted: bool = True
    def __init__(self, app: Optional[Flask]=None):
        self.app = app
        if app is not None:
            self._init_app(app)

    def init_app(self, app: Flask):
        self._init_app(app)
    
    def _init_app(self, flask_app: Flask):
        self.flask_app = flask_app
        flask_app.extensions["AutomationModules"] = self
        # Import all subclasses in that defined action module
        action_modules_package = importlib.import_module("app.action_modules")
        imported_modules = {}
        for loader, name, is_pkg in pkgutil.walk_packages(action_modules_package.__path__):
            full_name = action_modules_package.__name__ + '.' + name
            try:
                imported_modules[full_name] = importlib.import_module(full_name)
            except ModuleNotFoundError:
                continue
        # Rebuild all action modules - add default options to all of them
        #for am in self._action_modules:
        #    am.load_default_options(flask_app)
        

    @classmethod
    def register_action_module(cls, module):
        cls._action_modules.append(module)
        cls._sorted = False
    
    @property
    def action_modules(self):
        self._action_modules.sort(key=lambda x: x.title)
        return self._action_modules
    
    def get(self, module_name: str):
        for am in self._action_modules:
            if am.__class__.__name__ == module_name:
                return am
        return None

    class Meta:
        verbose_name = _l("Action Module")
        verbose_name_plural = _l("Action Modules")
        icon = 'icon-sword-smithing-svgrepo-com'
        project_permission_actions = {'index': _l("Show action modules list"), 'create': _l("Run action modules by target")}