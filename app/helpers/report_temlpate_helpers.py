from docxtpl import DocxTemplate, RichText
import re
from typing import List
from bs4 import BeautifulSoup


def convert_html_to_word(html_data: str | None, bold=False, italic=False, underline=False) -> RichText:
    if html_data is None:
        return RichText()
    soup = BeautifulSoup(html_data, 'html.parser')
    segments = []

    def get_highlight_from_style(style_str):
        """Extract background-color from style and return highlight title for docxtpl"""
        if not style_str:
            return None
        match = re.search(r'background-color:\s*([^;]+);?', style_str, re.IGNORECASE)
        if not match:
            return None
        bg_color = match.group(1).strip().lower()
        if 'hsl(60' in bg_color or bg_color in ('yellow', '#ffff00', 'rgb(255,255,0)'):
            return 'yellow'
        elif 'hsl(120' in bg_color or bg_color in ('green', '#00ff00', 'rgb(0,255,0)'):
            return 'green'
        elif 'hsl(0' in bg_color or bg_color in ('red', '#ff0000', 'rgb(255,0,0)'):
            return 'red'
        elif 'hsl(240' in bg_color or bg_color in ('blue', '#0000ff', 'rgb(0,0,255)'):
            return 'blue'
        return 'yellow'

    def parse(node, bold=False, italic=False, underline=False, highlight=None):
        if node.name is None:
            if node.string is not None:
                segments.append((node.string, bold, italic, underline, highlight))
            return
        
        new_bold = bold or node.name in ('b', 'strong')
        new_italic = italic or node.name in ('i', 'em')
        new_underline = underline or node.name == 'u'
        new_highlight = highlight
        
        if node.name == 'span' and node.get('style') and 'background-color' in node['style']:
            new_highlight = 'yellow'
        if node.name == 'br':
            segments.append(('\n', bold, italic, underline, highlight))
            return

        for child in node.children:
            parse(child, new_bold, new_italic, new_underline, new_highlight)

        if node.name == 'p':
            segments.append(('\a', bold, italic, underline, highlight))

    parse(soup, bold, italic, underline)
    if segments and segments[-1][0] in ['\a', '\n']:
        segments.pop()

    rt = RichText()
    for text, b, i, u, h in segments:
        rt.add(text, bold=b, italic=i, underline=u, highlight=h)
    return rt


def split_by_paragraphs(html_string: str | None) -> List[str]:
    if not html_string:
        return []
    paragraphs = re.findall(r'<p>(.*?)</p>', html_string, flags=re.DOTALL)
    return [p.strip() for p in paragraphs if p.strip()]
