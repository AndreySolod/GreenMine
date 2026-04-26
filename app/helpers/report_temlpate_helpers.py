from docxtpl import DocxTemplate, RichText
import re
from typing import List
from bs4 import BeautifulSoup


def convert_html_to_word(html_data: str, bold=False, italic=False, underline=False) -> RichText:
    soup = BeautifulSoup(html_data, 'html.parser')
    rt = RichText()

    def get_highlight_from_style(style_str):
        """Извлекает background-color из style и возвращает название highlight для docxtpl"""
        if not style_str:
            return None
        # Ищем background-color: ...;
        match = re.search(r'background-color:\s*([^;]+);?', style_str, re.IGNORECASE)
        if not match:
            return None
        bg_color = match.group(1).strip().lower()
        # Простейшее отображение: любые жёлтые/жёлто-зелёные тона -> yellow
        # Можно расширить для других цветов
        if 'hsl(60' in bg_color or bg_color in ('yellow', '#ffff00', 'rgb(255,255,0)'):
            return 'yellow'
        elif 'hsl(120' in bg_color or bg_color in ('green', '#00ff00', 'rgb(0,255,0)'):
            return 'green'
        elif 'hsl(0' in bg_color or bg_color in ('red', '#ff0000', 'rgb(255,0,0)'):
            return 'red'
        elif 'hsl(240' in bg_color or bg_color in ('blue', '#0000ff', 'rgb(0,0,255)'):
            return 'blue'
        # По умолчанию – жёлтый (наиболее частый маркер)
        return 'yellow'

    def parse(node, bold=False, italic=False, underline=False, highlight=None):
        # Текстовый узел – добавляем всё, что есть, включая пробелы
        if node.name is None:
            if node.string is not None:
                rt.add(node.string, bold=bold, italic=italic, underline=underline, highlight=highlight)
            return
        
        # Вычисляем новые стили для детей
        new_bold = bold or node.name in ('b', 'strong')
        new_italic = italic or node.name in ('i', 'em')
        new_underline = underline or node.name == 'u'
        new_highlight = highlight
        
        # Поддержка span с фоном (как было, highlight пока не работает, но оставляем)
        if node.name == 'span' and node.get('style') and 'background-color' in node['style']:
            # Можно оставить None или yellow — логика не изменится
            new_highlight = 'yellow'
        
        # Обрабатываем детей
        for child in node.children:
            parse(child, new_bold, new_italic, new_underline, new_highlight)
        
        if node.name == 'p':
            rt.add('\n')

    parse(soup, bold, italic, underline)
    return rt


def split_by_paragraphs(html_string: str | None) -> List[str]:
    if not html_string:
        return []
    # Находим всё между открывающим и закрывающим <p> (не жадный поиск)
    paragraphs = re.findall(r'<p>(.*?)</p>', html_string, flags=re.DOTALL)
    # Очищаем от лишних пробелов и пустых строк
    return [p.strip() for p in paragraphs if p.strip()]
