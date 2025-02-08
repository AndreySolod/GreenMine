from flask import Flask
from pybluemonday import UGCPolicy, Policy
from typing import List, Optional
from jinja2.filters import Markup


class TextSanitizerManager:
    ''' Sanitize all text to safety use with various WYSIWYG editos  '''
    def __init__(self, app: Optional[Flask]=None, policy: Policy=UGCPolicy(), allowed_attrs: Optional[List[str]]=["class", "style"]):
        self.policy = policy
        if allowed_attrs:
            self.policy.AllowAttrs(*allowed_attrs).Globally()
        if app:
            self.init_app(app)
        
    def init_app(self, app: Flask):
        app.extensions['TextSanitizer'] = self
    
    def sanitize(self, text: Optional[str]) -> Optional[str]:
        """ Sanitize text with current policy filters
        :param text: text to sanitize. May be a string or None"""
        if text is None or text == '':
            return text
        if not isinstance(text, str):
            raise TypeError("Paramether text must being a string or None!")
        return self.policy.sanitize(text)
    
    def escape(self, text: Optional[str], length: Optional[int] = None) -> Optional[str]:
        ''' Returned string that convert all tags values as escaped. Work via jinja2.filters.escape filter.
        :param text: text to sanitize;
        :param length: max text length, to which field would be truncated. '''
        if text is None:
            return None
        elif not isinstance(text, str):
            raise TypeError("Paramether text must being a string or None!")
        if length is None:
            return str(Markup.escape(text))
        elif not isinstance(length, int):
            raise TypeError("Paramether 'length' must being an Integer")
        while len(str(Markup.escape(text))) > length:
            text = text[:len(text) - 1:]
        return str(Markup.escape(text))
    
    def unescape(self, text: Optional[str]) -> Optional[str]:
        ''' Returned unescaped string. Work via jinja2.Markup.unescape filter '''
        if text is None:
            return None
        return str(Markup.unescape(text))