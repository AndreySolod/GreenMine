from flask import Flask, g, url_for, current_app
from typing import Optional, List, Dict
from markupsafe import Markup
from pathlib import PosixPath
import yaml


class RequiredLibraryError(Exception):
    pass


class RequiredLibrary:
    required_css_files: List[str]
    required_js_files: List[str]
    def __init__(self, required_css_files, required_js_files):
        if required_css_files is not None:
            self.required_css_files = required_css_files
        else:
            self.required_css_files = []
        if required_js_files is not None:
            self.required_js_files = required_js_files
        else:
            self.required_js_files = []
    
    def __repr__(self):
        return f"RequiredLibrary(required_css_files={self.required_css_files}, required_js_files={self.required_js_files})"


class SideLibraries:
    def __init__(self, app:Optional[Flask]=None, libraries_file: Optional[PosixPath]=None, always_required_libraries: List=[]):
        if libraries_file is not None:
            with open(libraries_file, 'r') as f:
                libraries = yaml.load(f, Loader=yaml.FullLoader)["libraries"]
            self.libraries = {key: RequiredLibrary(value["css"], value["js"]) for key, value in libraries.items()}
        else:
            self.libraries = None
        self.always_required_libraries = always_required_libraries
        if app:
            self.init_app(app)
        
    def init_app(self, app:Flask):
        app.jinja_env.globals["side_libraries"] = self
        app.extensions["SideLibraries"] = self
        @app.before_request
        def set_empty_library_required_list():
            g.LIBRARIES_REQUIRED = set()
            g.ADDITIONAL_SCRIPTS = set()
            g.LIBRARIES_REQUIRED.update(set(app.extensions["SideLibraries"].always_required_libraries))

    def library_required(self, library: str) -> None:
        if not library in self.libraries:
            raise RequiredLibraryError("This library is not registered!")
        g.LIBRARIES_REQUIRED.add(library)
    
    def is_library_required(self, library: str) -> bool:
        ''' Check if library, that setted in param library is required in current template
         :param library: library to check '''
        if library not in self.libraries:
            raise RequiredLibraryError("This library is not registered!")
        return library in g.LIBRARIES_REQUIRED
        
    def get_css_required_libraries(self):
        if self.libraries is None:
            return ''
        all_css = ''
        for library in g.LIBRARIES_REQUIRED:
            for css in self.libraries[library].required_css_files:
                all_css += f'<link rel="stylesheet" href="{url_for('static', filename=css)}">\n'
        return Markup(all_css)
    
    def get_js_required_libraries(self, csp_nonce:str=''):
        if self.libraries == None:
            return ''
        all_js = ''
        for library in g.LIBRARIES_REQUIRED:
            for js in self.libraries[library].required_js_files:
                all_js += f'<script nonce="{csp_nonce}" src="{url_for('static', filename=js)}"></script>\n'
        return Markup(all_js)
    
    def require_script(self, script: str):
        ''' Added a new script to page for render.
        :param script: string of javascript, that needed to <script></script> tags '''
        g.ADDITIONAL_SCRIPTS.add(script)
    
    def render_all_additional_scripts(self, csp_nonce:str=''):
        ''' Printing all scripts that added by modules on page.
         :params csp_nonce: Nonce for Content Security Policy that will be added to script '''
        return Markup("\n".join(map(lambda x: f'<script nonce="{csp_nonce}">{x}</script>', g.ADDITIONAL_SCRIPTS)))