from app import db, side_libraries, sanitizer
import re
import uuid
import math
from app.extensions.utf8strings import UTF8strings
import random
import json
import datetime
import functools
import yaml
import sys
from typing import List, Optional, Tuple, Any, TypedDict, Callable, TypeVar, Required, NotRequired
from flask_socketio import disconnect
from flask_login import current_user
from flask import url_for, abort, g, jsonify, Flask, Request, current_app
from app.extensions.moment import moment
from jinja2.filters import Markup
from flask_wtf.csrf import generate_csrf
import sqlalchemy as sa
from sqlalchemy import func
import sqlalchemy.exc as exc
from sqlalchemy.inspection import inspect
import sqlalchemy.orm as so
import sqlalchemy.sql.selectable as sa_selectable
from bs4 import BeautifulSoup
from sqlalchemy.orm.session import Session
import os
import os.path
import importlib
import logging
from flask_babel import lazy_gettext as _l
from pathlib import Path


def validates_ip(address: str, error_msg: str = _l("Incorrect IP-address"), error_type: Exception = ValueError) -> str:
    """
    Validates an IP address against a regular expression pattern.

    This function checks if the provided `address` is a valid IPv4 address. If the address is valid, it is returned as is.
    If the address is invalid, an exception of type `error_type` is raised with the message `error_msg`.

    Args:
        address (str): The IP address to validate.
        error_msg (str, optional): The error message to raise if the IP address is invalid. Defaults to "Incorrect IP-address".
        error_type (Exception, optional): The type of exception to raise if the IP address is invalid. Defaults to ValueError.

    Returns:
        str: The validated IP address.

    Raises:
        Exception: If the IP address is invalid, an exception of type `error_type` is raised with the message `error_msg`.
    """
    pattern = r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$"
    if re.match(pattern, address):
        return address
    else:
        raise error_type(str(error_msg))


def validates_port(port: int, error_type:Exception = ValueError) -> int:
    ''' Проверяет на корректность входные данные порта - находится ли он в диапазоне [0, 65535] '''
    if port < 0 or port > 65535:
        raise error_type("Порт должен находиться в диапазоне [0, 65535]")
    return port


def validates_mac(address: str, error_msg: str = _l("Incorrect MAC-addres"), error_type: Exception = ValueError) -> str:
    if re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", address.lower()):
        return address
    else:
        raise error_type(str(error_msg))


def default_string_slug() -> str:
    return str(uuid.uuid4())


def random_string(number_symbols: int) -> str:
    ''' Возвращает случайную строку заданной длины  '''
    first_symbol = random.choice(UTF8strings.ascii_uppercase)
    return first_symbol + ''.join(random.choices(UTF8strings.ascii_uppercase + UTF8strings.digits, k=number_symbols - 1))


def get_complementary_color(color: str) -> str:
    ''' Возвращает цвет, комплементарный к заданному. '''
    if color is None:
        return '#000000'
    if color.startswith('rgba'):
        c = color[5:]
        c = c[:len(c) - 1:]
        c1 = tuple(map(lambda x: round(float(x)), c.split(', ')[:3]))

        def clamp(x):
            return max(0, min(x, 255))

        color = "#{0:02x}{1:02x}{2:02x}".format(clamp(c1[0]), clamp(c1[1]), clamp(c1[2]))
    color = color[1:]
    color = int(color, 16)
    comp_color = 0xFFFFFF ^ color
    comp_color = "#%06X" % comp_color
    return comp_color


def state_button(state, is_archived: bool = False) -> str:
    rand_string = random_string(15)
    if not is_archived:
        res = f'''<div class="btn-group">
    <button type="button" class="btn btn-primary dropdown-toggle" id="{rand_string}" style="background-color: {state.color};color: {get_complementary_color(state.color)};border-radius: 19px;padding-top: 10px;padding-bottom: 3px;padding-left: 15px;margin-left:10px;margin-bottom:3em;" data-bs-toggle="dropdown" aria-expanded="false">{state.title}</button><ul class="dropdown-menu" aria-labelledby="{rand_string}">'''
        for s in state.can_switch_to_state:
            res += f'<li><a class="dropdown-item" href="#" style="background-color: {s.color};color: {get_complementary_color(s.color)}">{s.title}</a></li>'
        res += '</ul></div>'
    else:
        res = f''' <button type="button" class="btn btn-primary" id="{rand_string}" style="background-color: #808080;border-radius: 19px;padding-top: 10px;padding-bottom: 3px;padding-left: 15px;margin-left:10px;margin-bottom:3em;">{state.title}</button>'''
    return res


def task_tree_header(task, default_margin: int = 40, is_archived: bool = False) -> Markup:
    def html(task, default_margin: int) -> str:
        if task is None:
            return '', 0
        if task.parent_task is None:
            return f'<h6 style="font-size:12px;"><a class="text-muted" href="{url_for('tasks.projecttask_show', projecttask_id=task.id)}">{task.tracker.title} #{task.id}: {task.title}</a></h6>', 1
        else:
            parent_res, parent_count = html(task.parent_task, default_margin)
            return parent_res + f'<h6 style="margin-left:{parent_count * default_margin}px;font-size:12px;"><a class="text-muted" href="{url_for("tasks.projecttask_show", projecttask_id=task.id)}">{task.tracker.title} #{task.id}: {task.title}</a></h6>', parent_count + 1
    if task.parent_task_id is None:
        return Markup(f'''<h4 id="task-title">{task.title}</h4>''')
    parent_res, parent_count = html(task.parent_task, default_margin)
    now_res = f'''<h4 id="task-title" style="margin-left:{parent_count * default_margin}px;">{task.title}</h4>'''
    return Markup(parent_res + now_res)


class BreadCrumbs:
    def __init__(self, title, link, active=False):
        self.title = title
        self.link = link
        self.active = active


class SidebarElementSublink:
    def __init__(self, title: str, link: str, is_current_page: bool = False):
        self.title = title
        self.link = link
        self.is_current_page = is_current_page

    def sidebar(self) -> str:
        if (self.is_current_page):
            return "<li class='main-list-ul'><a href='{}' class=\"current-page\">{}</a></li>".format(self.link, self.title)
        else:
            return "<li class='main-list-ul'><a href='{}'>{}</a></li>".format(self.link, self.title)


class SidebarElement:
    def __init__(self, title: str, link: str, icon: str, is_current_page: bool = False, sublinks: List[SidebarElementSublink] = []):
        self.title = title
        self.link = link
        self.icon = icon
        self.sublinks = sublinks
        self.is_current_page = is_current_page

    def sidebar(self) -> str:
        if len(self.sublinks) == 0:
            res = '<li'
            if self.is_current_page:
                res += ' class="main-list-ul active selected"'
            res += '><a href="{}"><span class="has-icon"><i class="{}"></i></span><span class="nav-title">{}</span></a></li>'.format(self.link, self.icon, self.title)
        elif len(self.sublinks) != 0:
            res = '<li'
            if self.is_current_page:
                res += ' class="main-list-ul active selected"'
            res += '><a href="#" class="has-arrow" aria-expanded="false"><span class="has-icon"><i class="{}"></i></span><span class="nav-title">{}</span></a><ul aria-expanded="false" class="main-list-ul"'.format(self.icon, self.title)
            if self.is_current_page:
                res += ' class="main-list-ul collapse in"'
            res += ">"
            for s in self.sublinks:
                res += s.sidebar()
            res += '</ul></li>'
        return res


class CurrentObjectAction:
    def __init__(self, title: str, icon: str, link: str, action_type: str="a_href", confirm: str='', btn_class: str="btn-primary", method: str="GET"):
        self.title = title
        self.icon = icon
        self.link = link
        self.action_type = action_type
        self.confirm = confirm
        self.btn_class = btn_class
        self.method = method
        self.unique_identifier = random_string(10)

    def button(self) -> str:
        if not g.get('csrf_token'):
            generate_csrf()
        if self.method == 'GET':
            if (self.action_type == "a_href"):
                return '<a href="{}" class="btn {}" data-toggle="tooltip" data-placement="left" title="{}" {}><i class="{}"></i></a>'.format(self.link, self.btn_class, self.title, self.confirm, self.icon)
            elif (self.action_type == "button_modal"):
                return '<a href="#" class="btn {}" data-toggle="tooltip" data-bs-toggle="modal" data-bs-target="#{}" title="{}" {}><i class="{}"></i></a>'.format(self.btn_class, self.link, self.title, self.confirm, self.icon)
        elif self.method == 'DELETE':
            element_id = 'a_confirm' + random_string(20)
            script = f"document.getElementById('{element_id}').addEventListener('click', function() {{if(confirm('{self.confirm}')) {{ document.getElementById('{self.unique_identifier}').submit() }} }});"
            side_libraries.require_script(script)
            return f'<a id="{element_id}" class="btn {self.btn_class}" data-toggle="tooltip" data-placement="left" title="{self.title}" ><i class="{self.icon}"></i></a><form id="{self.unique_identifier}" action="{self.link}" method="POST"><input type="hidden" name="csrf_token" value="{g.csrf_token}" /></form>'
        elif self.method == 'POST':
            element_id = 'a_confirm' + random_string(20)
            script = f"document.getElementById('{element_id}').addEventListener('click', function() {{ document.getElementById('{self.unique_identifier}').submit() }});"
            side_libraries.require_script(script)
            return f'<a id="{element_id}" class="btn {self.btn_class}" data-toggle="tooltip" data-placement="left" title="{self.title}" ><i class="{self.icon}"></i></a><form id="{self.unique_identifier}" action="{self.link}" method="POST"><input type="hidden" name="csrf_token" value="{g.csrf_token}" /></form>'



class CurrentObjectInfo:
    def __init__(self, title: str, icon: str, subtitle: str = '', actions: List[CurrentObjectAction] = []):
        self.title = title
        self.icon = icon
        self.subtitle = subtitle
        self.actions = actions

    def print_actions(self) -> str:
        if (len(self.actions) != 0):
            return ''.join([i.button() for i in self.actions])
        return ''


def truncate_html_words(s: str, num: int, end_text: str = '...') -> str:
    """Truncates HTML to a certain number of words (not counting tags and
    comments). Closes opened tags if they were correctly closed in the given
    html. Takes an optional argument of what should be used to notify that the
    string has been truncated, defaulting to ellipsis (...).

    Newlines in the HTML are preserved.

    This is just a version of django.utils.text.truncate_html_words with no space before the end_text.
    """
    length = int(num)
    if length <= 0:
        return u''
    html4_singlets = ('br', 'col', 'link', 'base', 'img', 'param', 'area', 'hr', 'input')
    # Set up regular expressions
    re_words = re.compile(r'&.*?;|<.*?>|(\w[\w-]*)', re.U)
    re_tag = re.compile(r'<(/)?([^ ]+?)(?: (/)| .*?)?>')
    # Count non-HTML words and keep note of open tags
    pos = 0
    end_text_pos = 0
    words = 0
    open_tags = []
    while words <= length:
        m = re_words.search(s, pos)
        if not m:
            # Checked through whole string
            break
        pos = m.end(0)
        if m.group(1):
            # It's an actual non-HTML word
            words += 1
            if words == length:
                end_text_pos = pos
            continue
        # Check for tag
        tag = re_tag.match(m.group(0))
        if not tag or end_text_pos:
            # Don't worry about non tags or tags after our truncate point
            continue
        closing_tag, tagname, self_closing = tag.groups()
        tagname = tagname.lower()  # Element names are always case-insensitive
        if self_closing or tagname in html4_singlets:
            pass
        elif closing_tag:
            # Check for match in open tags list
            try:
                i = open_tags.index(tagname)
            except ValueError:
                pass
            else:
                # SGML: An end tag closes, back to the matching start tag,
                # all unclosed intervening start tags with omitted end tags
                open_tags = open_tags[i+1:]
        else:
            # Add it to the start of the open tags list
            open_tags.insert(0, tagname)
    if words <= length:
        # Don't try to close tags if we don't need to truncate
        return s
    out = s[:end_text_pos]
    if end_text:
        out += end_text
    # Close any tags still open
    for tag in open_tags:
        out += '</%s>' % tag
    # Return string
    return out


def escapejs(string: str | dict) -> Markup:
    ''' convert string to safe string that can safety insert into JavaScript code.
     :param string: String to convert.
      
    <script>
        let my_string = '{{ some_string|escapejs }}';
    </script>

    Written partially from django funciton escapejs
    '''
    _js_escapes = {
        ord("\\"): "\\u005C",
        ord("'"): "\\u0027",
        ord('"'): "\\u0022",
        ord(">"): "\\u003E",
        ord("<"): "\\u003C",
        ord("&"): "\\u0026",
        ord("="): "\\u003D",
        ord("-"): "\\u002D",
        ord(";"): "\\u003B",
        ord("`"): "\\u0060",
        ord("\u2028"): "\\u2028",
        ord("\u2029"): "\\u2029",
    }
    # Escape every ASCII character with a value less than 32.
    _js_escapes.update((ord("%c" % z), "\\u%04X" % z) for z in range(32))
    if isinstance(string, dict):
        string = json.dumps(string)
    return Markup(string.translate(_js_escapes))


def as_style(attrs: dict) -> Markup:
    ''' Convert current dict to Markup string that we can insert into jinja2 template directly.
     :param dict: dictonaries that contain key:value association to style.
      
    {% let style_dict = {'padding': '10px', 'color': 'blue'} %}
    <div class="my-class" {{ style_dict|as_style_attrs }}></div>
     
    -> <div class="my-class" style="padding:10px;color:blue'''
    return Markup(f'''style="{';'.join([f"{key}:{value}" for key, value in attrs.items()])}"''')


class Page(object):

    def __init__(self, items, page, page_size, total):
        self.items = items
        self.previous_page = None
        self.next_page = None
        self.has_previous = page > 1
        if self.has_previous:
            self.previous_page = page - 1
        previous_items = (page - 1) * page_size
        self.has_next = previous_items + len(items) < total
        if self.has_next:
            self.next_page = page + 1
        self.total = total
        self.pages = int(math.ceil(total / float(page_size)))


def paginate(select, model, page: int, page_size: int):
    if page <= 0:
        raise AttributeError('page needs to be >= 1')
    if page_size <= 0:
        raise AttributeError('page_size needs to be >= 1')
    items = db.session.scalars(select.limit(page_size).offset((page - 1) * page_size)).all()
    total = db.session.scalar(sa.select(func.count()).select_from(model))
    return Page(items, page, page_size, total)


def bootstrap_table_argument_parsing(request: Request) -> Tuple[str, str, str, Optional[int], Optional[int], dict, List]:
    search = request.args.get('search') or ''
    sort = request.args.get('sort')
    order = request.args.get('order')
    if order not in ['asc', 'desc', None]:
        abort(400)
    try:
        offset = int(request.args.get('offset'))
    except (ValueError):
        abort(400)
    except (TypeError):
        offset = None
    try:
        limit = int(request.args.get('limit'))
    except ValueError:
        abort(400)
    except TypeError:
        limit = None
    if 'filter' in request.args:
        filter_data = json.loads(request.args.get('filter'))
    else:
        filter_data = {}
    # Разбираем MultiSort
    multi_sort_dict = {}
    for arg in request.args:
        if arg.startswith('multiSort'):
            arg_numb = re.search(r'\[\d+\]', arg)
            if arg_numb is None:
                abort(400)
            arg_numb = int(arg_numb[0][1:len(arg_numb[0]) - 1:])
            arg_name = re.search(r'\[sort(.*?)\]', arg)
            if arg_name is None:
                abort(400)
            arg_name = arg_name[0][1:len(arg_name[0]) - 1:]
            arg_value = request.args.get(arg)
            if arg_numb in multi_sort_dict:
                multi_sort_dict[arg_numb][arg_name] = arg_value
            else:
                multi_sort_dict[arg_numb] = {arg_name: arg_value}
    multi_sort = []
    for key in sorted(list(multi_sort_dict.keys())):
        multi_sort.append(multi_sort_dict[key])
    return search, sort, order, offset, limit, filter_data, multi_sort


def find_data_by_request_params(obj: Any, request: Request, column_index: Optional[List[str]]=None):
    #db.engine.echo = True
    ''' Выполняет поиск заданных объектов типа obj, получая параметры поиска из запроса (request). Возвращает 2 sql-запроса: на получение всех объектов, соответствующих заданным параметрам, а также на получение количества таких объектов. Для получения соответствующих объектов, нужно вызвать session.scalars(sql).all() '''
    # Собираем аргументы
    search, sort, order, offset, limit, filter_data, multi_sort = bootstrap_table_argument_parsing(request)
    # Все аргументы разобраны. Начинаем построение sql:
    sql = sa.select(obj)
    # Дополнительный SQL для подсчёта количества объектов
    sql_count = sa.select(func.count(obj.id.distinct())).select_from(obj)
    # Все простые атрибуты:
    if column_index is None:
        column_index = obj.Meta.column_index
    simple_attrs = [i for i in column_index if i in inspect(obj).column_attrs.keys()]
    # Все отношения
    rels = [i for i in column_index if i in inspect(obj).relationships.keys() and not inspect(obj).relationships[i].uselist]
    rels_uselist = [i for i in column_index if i in inspect(obj).relationships.keys() and inspect(obj).relationships[i].uselist]
    # Join'ы и их условия обработаем вместе с условиями where
    list_joins = []
    # Теперь обрабатываем условие Where, и вместе с ним - joins. Начнём с поиска - Он заключается в db.or_
    where_search = []
    dict_aliases = {}  # Словарь ассоциаций - атрибут - его alias. В дальнейшем будет использоваться для условий Where
    for a in column_index:
        # Объект относится к простым атрибутам
        if a in simple_attrs:
            where_search.append(sa.cast(getattr(obj, a), sa.String).ilike('%' + search + '%'))
        # Объект - отношение без пути. Тогда он интерпретируется как атрибут title этого объекта
        elif a in rels:
            dict_aliases[a] = so.aliased(getattr(obj, a).entity.class_)
            list_joins.append(getattr(obj, a).of_type(dict_aliases[a]))
            where_search.append(dict_aliases[a].title.ilike('%' + search + '%'))
        # Объект - отношение, представленное списком
        elif a in rels_uselist:
            dict_aliases[a] = so.aliased(getattr(obj, a).entity.class_)
        # Объект - отношение с путём. Объект интерпретируется как путь до отношения
        else:
            attr_name = a.split('-')[0].split('.')[0]
            now_attr = getattr(obj, attr_name)
            for num_pos, attr in enumerate(a.split('-')[0].split('.')[1::]):
                prefix_attr = '.'.join(a.split('-')[0].split('.')[:num_pos + 1:])
                if prefix_attr not in dict_aliases:
                    dict_aliases[prefix_attr] = so.aliased(now_attr.entity.class_)
                    list_joins.append(now_attr.of_type(dict_aliases[prefix_attr]))
                now_attr = getattr(now_attr.entity.class_, attr)
            attr_name = a.split('-')[0].split('.')[-1]
            now_attr = getattr(dict_aliases[prefix_attr], attr_name)
            where_search.append(sa.cast(now_attr, sa.String).ilike('%' + search + '%'))
    # Добавим условия join'ов:
    for j in list_joins:
        sql = sql.join(j, isouter=True)
        sql_count = sql_count.join(j, isouter=True)
    # Отдельно - загрузка всех не M2M-объектов в joinedload - это нужно для получения возможности фильтрации по ним
    for a in column_index:
        if a in rels:
            sql = sql.options(so.joinedload(getattr(obj, a)))
        elif a not in simple_attrs and a not in rels_uselist:
            attr_name = a.split('-')[0].split('.')[0]
            now_attr = getattr(obj, attr_name)
            load_chain = so.joinedload(now_attr)
            is_list = inspect(obj).relationships[attr_name].uselist
            for num_pos, attr in enumerate(a.split('-')[0].split('.')[1:len(a.split('-')[0].split('.')) - 1:]):
                if inspect(now_attr.entity.class_).relationships[attr].uselist:
                    is_list = True
                    break
                now_attr = getattr(now_attr.entity.class_, attr)
                load_chain.joinedload(now_attr)
            if is_list:
                continue
            sql = sql.options(load_chain)
    # Теперь обрабатываем where - фильтры. Они заключаются в db.and_
    where_filter = []
    for a, val_a in filter_data.items():
        if a in simple_attrs:
            # a - простой атрибут
            # Если a - это атрибут типа boolean, то нужно использовать не сопоставление со строкой, а сопоставление со значением:
            if isinstance(getattr(obj, a).type, sa.Boolean):
                where_filter.append(getattr(obj, a) == (val_a == 'true'))
            else: # Иначе - сопоставление со строкой
                where_filter.append(sa.cast(getattr(obj, a), sa.String).ilike('%' + str(val_a) + '%'))
        elif a in rels or a in rels_uselist:
            # a - записывается как атрибут 'id' данного отношения, и поэтому интерпретируется соответствующе
            try:
                val_a = int(val_a)
            except (ValueError, TypeError):
                continue
            where_filter.append(getattr(obj, a + '_id') == sa.cast(val_a, sa.Integer))
        else:
            # a - это сложное отношение (например, атрибут атрибута). Он может принимать 2 состояния: "input" и "select", записывается как path.to.attr-input
            try:
                attr_path = a.split('-')[0].split('.')
                attr_name = ".".join(attr_path[:len(attr_path) - 1:])
                now_attr = getattr(dict_aliases[attr_name], attr_path[-1])
                if a.split('-')[1] == 'input':
                    where_filter.append(sa.cast(now_attr, sa.String).ilike('%' + val_a + '%'))
                elif a.split('-')[1] == 'select':
                    try:
                        val_a = int(val_a)
                    except (ValueError, TypeError):
                        continue
                    where_filter.append(now_attr == sa.cast(val_a, sa.Integer))
            except KeyError:
                abort(400)
    where_all = sa.and_(True, sa.or_(*where_search), sa.and_(True, *where_filter))
    # Добавляем эти условия в sql:
    sql = sql.where(where_all)
    sql_count = sql_count.where(where_all)
    # Теперь обработаем упорядочивание элементов:
    for e in multi_sort:
        if e["sortName"] in simple_attrs:
            sql = sql.order_by(getattr(getattr(obj, e["sortName"]), e['sortOrder'])())
        elif e["sortName"] in rels or e['sortName'] in rels_uselist:
            sql = sql.order_by(getattr(dict_aliases[e['sortName']].title, e['sortOrder'])())
        else:
            pass
    # Отдельно необходимо обработать операцию простой сортировки:
    if sort is not None and order is not None:
        if sort in simple_attrs:
            sql = sql.order_by(getattr(getattr(obj, sort), order)())
        elif sort in rels:
            sql = sql.order_by(getattr(dict_aliases[sort].title, order)())
        elif sort not in rels_uselist:
            attr_path = sort.split('-')[0].split('.')
            attr_name = ".".join(attr_path[:len(attr_path) - 1:])
            sql = sql.order_by(getattr(getattr(dict_aliases[attr_name], attr_path[-1]), order)())
    # Теперь обработаем limit и offset - они обрабатываются очень просто
    sql = sql.limit(limit).offset(offset)
    # Отдельно - указание на поиск уникальных объектов (поскольку выполняем, в том числе, и Many-To-Many Join'ы):
    #sql = sql.distinct()
    #sql_count = sql_count.distinct()
    return sql, sql_count


T = TypeVar('T')


class BootstrapTableSearchParams(TypedDict):
    obj: Required[T] # Объект поиска
    column_index: Required[List[str]] # Список столбцов, которые будут отображаться, и по которым будет производиться поиск.
    print_params: NotRequired[List[Tuple[str, Callable[[T], str]]]] # Параметры отображения заданной строки на экране (такие как раскраска в цвета и т.п.).
    base_select: Required[Callable[[sa_selectable.Select], sa_selectable.Select]] # Базовый запрос, который будет использоваться для поиска данных.


def get_bootstrap_table_json_data(request: Request, additional_params: BootstrapTableSearchParams):
    obj = additional_params['obj']
    if 'column_index' in additional_params:
        column_index = additional_params['column_index']
    else:
        column_index = obj.Meta.column_index
    print_params = additional_params.get('print_params')
    sql, sql_count = find_data_by_request_params(obj, request, column_index=column_index)
    sql = db.session.scalars(additional_params["base_select"](sql)).all()
    # Теперь сохраняем данные в json и возвращаем их:
    lst = []
    for i in sql:
        now_attr = {}
        for col in column_index:
            # Текущий столбец - это или простой атрибут
            if col in inspect(obj).column_attrs.keys():
                if col == 'description':
                    if i.description is not None:
                        now_attr[col] = sanitizer.escape(sanitizer.pure_text(truncate_html_words(i.description, 20)))
                    else:
                        now_attr[col] = ''
                elif isinstance(getattr(obj, col).type, sa.DateTime):
                    now_attr[col] = moment(getattr(i, col)).format('LLLL')
                elif isinstance(getattr(obj, col).type, sa.Boolean):
                    now_attr[col] = str(_l("Yes")) if getattr(i, col) else str(_l("No"))
                else:
                    value_now_attr = getattr(i, col)
                    now_attr[col] = str(value_now_attr) if value_now_attr is not None else '-'
            # Или представлен отношением - в этом случае берётся атрибут title у отношения
            elif col in inspect(obj).relationships.keys():
                if not inspect(obj).relationships[col].uselist: # Отношение - это простое отношение, т.е. не использующее список
                    now_attr[col] = getattr(getattr(i, col), 'title', None)
                else: # Отношение использует список. В этом случае мы берём первые m2m_max_items элементов и соединяем их через m2m_join_symbol 
                    rel_class = inspect(obj).relationships[col].entity.class_
                    first_elems = current_app.config["GlobalSettings"].m2m_join_symbol.join(map(str,
                        db.session.scalars(sa.select(rel_class.title).select_from(obj).join(getattr(obj, col)).where(obj.id == i.id)
                                           .limit(current_app.config['GlobalSettings'].m2m_max_items)).all()))
                    total_m2m_elems = db.session.scalars(sa.select(sa.func.count()).select_from(obj).join(getattr(obj, col)).where(obj.id == i.id)).first()
                    if total_m2m_elems > current_app.config['GlobalSettings'].m2m_max_items:
                        first_elems += current_app.config['GlobalSettings'].m2m_join_symbol + str(_l("Total: %(total)s elements", total=total_m2m_elems))
                    now_attr[col] = first_elems
            # Или является составным атрибутом без пути - т.е. имеет отношение "Многие ко многим", имеет один атрибут и использует Input вместо Select:
            elif len(col.split("-")[0].split(".")) == 2 and inspect(obj).relationships[col.split('-')[0].split('.')[0]].uselist:
                curr_obj_name, curr_obj_attr = col.split('-')[0].split('.')
                alias_1 = inspect(obj).relationships[curr_obj_name].entity.class_
                alias_2 = so.aliased(obj)
                first_elems_sql = sa.select(getattr(alias_1, curr_obj_attr)).select_from(alias_2).join(getattr(alias_2, curr_obj_name)).where(alias_2.id == i.id)
                first_elems_sql = first_elems_sql.limit(current_app.config['GlobalSettings'].m2m_max_items)
                first_elems = current_app.config["GlobalSettings"].m2m_join_symbol.join(map(str, db.session.scalars(first_elems_sql).all()))
                total_m2m_elems = db.session.scalars(sa.select(sa.func.count()).select_from(alias_2).join(getattr(alias_2, curr_obj_name)).where(alias_2.id == i.id)).first()
                if total_m2m_elems > current_app.config['GlobalSettings'].m2m_max_items:
                    first_elems += current_app.config['GlobalSettings'].m2m_join_symbol + str(_l("Total: %(total)s item(s)", total=total_m2m_elems))
                now_attr[col] = first_elems
            # Или является сложным атрибутом - в этом случае берётся путь этого объекта:
            else:
                current_object = i
                path = col.split('-')[0].split('.')
                if col.split('-')[1] == 'input':
                    for attr in path:
                        if current_object is None:
                            current_object = ''
                            break
                        current_object = getattr(current_object, attr)
                elif col.split('-')[1] == 'select':
                    # В этом случае вместо последнего атрибута берём атрибут 'title'
                    for attr in path[:len(path) - 1:]:
                        current_object = getattr(current_object, attr, None)
                    current_object = getattr(current_object, 'title', None)
                if current_object is not None:
                    now_attr[col] = str(current_object)
                #else:
                #    now_attr[col] = '-'
        if print_params is not None:
            for col, called_func in print_params:
                now_attr[col] = called_func(i)
        lst.append(now_attr)
    #sql_total_not_filtered = sa.select(func.count()).select_from(additional_params['obj'])
    #if 'base_select' in additional_params:
    #    sql_total_not_filterd = additional_params['base_select'](sql_total_not_filtered)
    if 'base_select' in additional_params:
        sql_count = additional_params['base_select'](sql_count)
    total = db.session.scalars(sql_count).one()
    return jsonify({'total': total, "rows": lst})


def get_or_404(session: Session, model, identifier: int):
    obj = session.get(model, identifier)
    if obj is None:
        abort(404)
    return obj


def is_empty_string(string: str) -> bool:
    if string is None:
        return True
    s = BeautifulSoup(string, 'lxml').text
    s = re.sub("[ \n\t]", "", s)
    return len(s) == 0


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped


def check_global_settings_on_init_app(app: Flask, logger: logging.Logger) -> None:
    import app.models as models
    """ Check global settings on application when create an application instance """
    with app.app_context():
        def create_application_languages():
            root = os.path.join(os.path.dirname(app.root_path), 'default_database_value') # Migragion root
            init_db_val_file = os.path.join(root, 'application_languages.yml')
            with open(init_db_val_file, 'r') as f:
                read_data = yaml.load(f, Loader=yaml.FullLoader)
            for app_language in read_data['ApplicationLanguage']:
                ss = next(iter(app_language.keys()))
                lang = models.ApplicationLanguage(string_slug=ss)
                for key_name, key_value in app_language[ss].items():
                    setattr(lang, key_name, key_value)
                db.session.add(lang)
            db.session.commit()
        
        def create_global_settings():
            ''' Create GlobalSettings object '''
            root = os.path.join(os.path.dirname(app.root_path), 'default_database_value') # Migragion root
            init_db_val_file = os.path.join(root, 'GlobalSettings.yml')
            with open(init_db_val_file, 'r') as f:
                read_data = yaml.load(f, Loader=yaml.FullLoader)
            gs = models.GlobalSettings()
            simple_attrs = inspect(models.GlobalSettings).column_attrs.keys()
            for key_name, key_value in read_data["GlobalSettings"].items():
                if key_name in simple_attrs:
                    setattr(gs, key_name, key_value)
                else:
                    try:
                        now_attr_cls = inspect(models.GlobalSettings).relationships[key_name].entity.class_
                        now_attr_value = db.session.scalars(sa.select(now_attr_cls).where(now_attr_cls.string_slug == key_value)).one()
                        setattr(gs, key_name, now_attr_value)
                    except (exc.MultipleResultsFound, exc.NoResultFound, AttributeError, KeyError):
                        logger.critical("Error when parsing GlobalSettings file. Exited")
                        exit()
            db.session.add(gs)
            db.session.commit()
            gs = db.session.scalars(sa.select(models.GlobalSettings)).one()
            lang = gs.default_language
            db.session.expunge(gs)
            db.session.expunge(lang)
            app.config["GlobalSettings"] = gs
            app.config["GlobalSettings"].default_language = lang
            app.config["GlobalSettings"] = gs
        
        def check_default_values():
            ''' Checks default values in database and add default value if they not exist '''
            # administrator position - at least one position
            models = importlib.import_module('app.models')
            admin_position = db.session.scalars(sa.select(models.UserPosition).where(models.UserPosition.is_administrator == True)).first()
            if admin_position is None:
                admin_position = db.session.scalars(sa.select(models.UserPosition).where(models.UserPosition.string_slug == 'admin')).first()
                if admin_position is None:
                    logger.warning('Created new position "administrator"')
                    admin_position = models.UserPosition(title="Administrator", string_slug="admin", is_default=False)
                admin_position.is_administrator = True
                db.session.add(admin_position)
                db.session.commit()
            # admin - at least one person
            u = db.session.scalars(sa.select(models.User).join(models.User.position, isouter=True).where(models.UserPosition.is_administrator == True)).all()
            if len(u) == 0:
                logger.warning('User with administrator role is not exist.')
                a = db.session.scalars(sa.select(models.User).where(models.User.login == 'admin')).first()
                if a is None:
                    logger.warning('Created new admin user with login "admin" and password "admin"')
                    a = models.User(login='admin', string_slug='admin', first_name='Admin', last_name='GreenMine', email='admin@localhost.com', position=admin_position)
                    a.manager = a
                    a.set_password('admin')
                else:
                    logger.warning("Administrator rights have been added to the existing user 'admin'")
                    a.position = admin_position
                db.session.add(a)
                db.session.commit()
                logger.warning('Changes have been made to the database')
            # Project Roles - exist anonymous role
            r = db.session.scalars(sa.select(models.ProjectRole).where(models.ProjectRole.string_slug == 'anonymous')).first()
            if r is None:
                logger.warning('Anonymous project role does not exist. Create one')
                r = models.ProjectRole(string_slug='anonymous', title=str(_l("Anonymous")), description='Роль, присваиваемая пользователям, не участвующим в проекте')
                db.session.add(r)
                db.session.commit()
                logger.warning('Anonymous project role created')
            # All users have an preferred language
            users = db.session.scalars(sa.select(models.User)).all()
            for u in users:
                if u.preferred_language is None:
                    u.preferred_language = db.session.scalars(sa.select(models.ApplicationLanguage).where(models.ApplicationLanguage.string_slug == 'auto')).one()
                if u.position is None:
                    pos = db.session.scalars(sa.select(models.UserPosition).where(models.UserPosition.is_default == True)).first()
                    if pos is None:
                        pos = db.session.scalars(sa.select(models.UserPosition)).first()
                        if pos is None:
                            logger.warning("No default position found. Created new position")
                            pos = models.UserPosition(title="Administrator", string_slug="administrator", is_administrator=True, is_default=False)
                            db.session.add(pos)
                            db.session.commit()
                    u.position = pos
        
        def create_issue_templates():
            ''' Check if all issue templates are exist in database, and if not exist - create them '''
            from app.models import IssueTemplate
            root = Path(app.root_path).parent / 'default_database_value'
            init_db_val_file = root / 'issue_templates.yml'
            with open(init_db_val_file, 'r') as f:
                read_data = yaml.load(f, Loader=yaml.FullLoader)
            for template_slug, template_attrs in read_data.items():
                templ = db.session.scalars(sa.select(IssueTemplate).where(IssueTemplate.string_slug == template_slug)).first()
                if templ is None:
                    logger.warning(f'Issue template "{template_slug}" is missing. Created one')
                    templ = IssueTemplate(string_slug=template_slug)
                    for attr_name, attr_value in template_attrs.items():
                        setattr(templ, attr_name, attr_value)
                    db.session.add(templ)
                    db.session.commit()
        
        #Application languages
        try:
            auto_language = db.session.scalars(sa.select(models.ApplicationLanguage).where(models.ApplicationLanguage.string_slug == 'auto')).one()
        except (exc.NoResultFound, exc.MultipleResultsFound):
            logger.warning('Your database is corrupt. Must exist language with string_slug "auto". Recreating table "application_language"')
            logger.info("Cleaned table")
            all_languages = db.session.scalars(sa.select(models.ApplicationLanguage)).all()
            for l in all_languages:
                db.session.delete(l)
            db.session.commit()
            logger.info('Table successfully cleanded. Added data to table.')
            create_application_languages()
        except (exc.OperationalError): # database instance is not created yet
            logger.error("Table 'application_languages' does not exist. Try to execute 'flask db upgrade && FLASK_APP=GreenMine flask greenmine-command load-default-database'")
            sys.exit(1)
        all_languages = db.session.scalars(sa.select(models.ApplicationLanguage.code).where(models.ApplicationLanguage.string_slug != 'auto')).all()
        app.config["LANGUAGES"] = all_languages
        # Values required for correct operation
        check_default_values()
            
        # Global settings
        try:
            global_settings = db.session.scalars(sa.select(models.GlobalSettings)).one()
            # check if current global settings has an application language:
            if global_settings.default_language is None:
                logger.warning('Default language of application is None. Set to language "Auto"')
                global_settings.default_language = auto_language
                db.session.commit()
            global_settings = db.session.scalars(sa.select(models.GlobalSettings)).one()
            lang = global_settings.default_language
            db.session.expunge(global_settings)
            db.session.expunge(lang)
            app.config["GlobalSettings"] = global_settings
            app.config["GlobalSettings"].default_language = lang
            app.password_policy_manager.activate = global_settings.authentication_method == 'password'
        except exc.NoResultFound:
            logger.warning("Instance of Global Settings is not exist. Getting default instance")
            create_global_settings()
            logger.info("New instance is created")
        except exc.MultipleResultsFound:
            logger.warning("Your database is corrupt. Must exist only one instance of Global Settings")
            logger.info("Dropped all Global Settings Instance")
            gss = db.session.scalars(sa.select(models.GlobalSettings)).all()
            for i in gss:
                db.session.delete(i)
            db.session.commit()
            logger.info("Instances dropped. Create new instance of GlobalSetting from file GlobalSettings.yml")
            create_global_settings()
            logger.info("New instance is created")
        except exc.OperationalError:  # Database instance is not created
            logger.error("Database instance is not exist. Try call 'FLASK_APP=GreenMine flask db upgrade' in the command line")
            sys.exit(1)
        
        # issue templates
        create_issue_templates()


def get_global_objects_with_permissions():
    models = filter(lambda x: hasattr(x, 'Meta') and hasattr(x.Meta, 'global_permission_actions'), [i.class_ for i in db.Model.registry.mappers])
    for i in models:
        yield i