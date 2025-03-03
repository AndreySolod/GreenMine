from flask import Flask
from pybluemonday import UGCPolicy, Policy
from typing import List, Optional
from jinja2.filters import Markup
from bs4 import BeautifulSoup


class TextSanitizerManager:
    ''' Sanitize all text to safety use with various WYSIWYG editos  '''
    def __init__(self, app: Optional[Flask]=None, policy: Policy=UGCPolicy(), allowed_attrs: Optional[List[str]]=["class", "style"]):
        self.policy = policy
        if allowed_attrs:
            self.policy.AllowAttrs(*allowed_attrs).Globally()
        if app:
            self.init_app(app)
        
    def init_app(self, app: Flask):
        if not hasattr(app, 'extensions'):  # pragma: no cover
            app.extensions = {}
        app.extensions['TextSanitizer'] = self
        app.jinja_env.globals['sanitizer'] = self
    
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
    
    def pure_text(self, text: Optional[str]) -> str:
        ''' returned text, that are cleaned from all html tags. Cleaned via BeautifulSoup(text, 'lxml').text
        :param text: text to clean from html tags. May be None, than returned an empty string '''
        if text is None:
            return ''
        return BeautifulSoup(text, 'lxml').text
    
    def markup(self, text: Optional[str]) -> str:
        ''' returned text, that marked as "HTML Safe" and can insert into template without any escapes or cleaned.
        :param text: Optional text for mark as Markupsafe. If None - returned Markup text of empty string. '''
        if text is None:
            return Markup("")
        return Markup(text)