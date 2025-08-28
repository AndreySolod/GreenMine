import flask_wtf
from flask import abort, g, url_for
from wtforms import fields, widgets
from app.helpers.general_helpers import escapejs
import wtforms
from wtforms.fields.choices import SelectField, SelectMultipleField
from wtforms import ValidationError
import datetime
from app import db, side_libraries, sanitizer
from app.helpers.general_helpers import random_string
import json
import sqlalchemy as sa
import sqlalchemy.orm.collections as sacollections
from sqlalchemy.orm.session import Session as SessionBase
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from flask_babel import lazy_gettext as _l
from typing import Callable, Optional, Any, List, Tuple, Generator
from jinja2.filters import Markup


def populate_object(session: SessionBase, o: Any, field: str, value):
    simple_fields = inspect(o.__class__).column_attrs.keys()
    relations = inspect(o.__class__).relationships.keys()
    if field in simple_fields and not field.endswith('_id'):
        column = inspect(o.__class__).column_attrs[field].columns[0]
        if column.type.python_type == datetime.timedelta and value is not None:
            setattr(o, field, datetime.timedelta(hours=value))
        elif column.type.python_type == str and (column.type.length or column.info.get('was_escaped')):
            setattr(o, field, sanitizer.escape(value, column.type.length))
        elif column.type.python_type == str and not column.type.length and not column.info.get('was_escaped'):
            setattr(o, field, sanitizer.sanitize(value)) # Bleached data if they are does not have length - this is fields like WysiwygField
        elif column.type.__class__.__name__ == 'Enum':
            setattr(o, field, getattr(column.type.python_type, value))
        else:
            setattr(o, field, value)
    elif (field in simple_fields) and value is not None and (int(value) > 0):
        setattr(o, field, (int(value)))
    elif (field in simple_fields) and ((value is None) or (int(value) <= 0)):
        setattr(o, field, None)
    elif field in relations:
        uselist = inspect(o.__class__).relationships[field].uselist
        cls_rel = inspect(o.__class__).relationships[field].entity.class_
        coerce = set if isinstance(getattr(o, field), sacollections.InstrumentedSet) else list
        if uselist:
            lst = coerce(session.scalars(sa.select(cls_rel).where(cls_rel.id.in_(list(map(int, value))))).all())
            setattr(o, field, lst)
        else:
            elem = session.get(cls_rel, int(value))
            setattr(o, field, elem)


class FlaskForm(flask_wtf.FlaskForm):
    def populate_obj(self, session: SessionBase, o, current_user=None):
        for name, field in self._fields.items():
            if name == 'id':
                continue
            if field.__class__.__name__ == 'FileField' or field.__class__.__name__ == 'MultipleFileField':
                continue
            populate_object(session, o, name, field.data)
        if 'created_by_id' in inspect(o.__class__).column_attrs.keys() and current_user is not None and o.created_by is None:
            setattr(o, 'created_by_id', current_user.id)
        elif 'created_by_id' in inspect(o.__class__).column_attrs.keys() and current_user is not None and o.created_by is None:
            setattr(o, 'updated_by_id', current_user.id)

    def load_exist_value(self, o):
        simple_fields = inspect(o.__class__).column_attrs.keys()
        for name, field in self._fields.items():
            if (hasattr(o, name)) and (name in simple_fields) and not (name.endswith('_id')):
                if inspect(o.__class__).column_attrs[name].columns[0].type.python_type == datetime.timedelta and getattr(o, name) is not None:
                    field.data = getattr(o, name).seconds // 60 // 60
                elif isinstance(field, fields.StringField) or isinstance(field, fields.TextAreaField):
                    field.data = sanitizer.unescape((getattr(o, name)))
                elif inspect(o.__class__).column_attrs[name].columns[0].type.__class__.__name__ == 'Enum':
                    field.data = getattr(o, name).name
                else:
                    field.data = getattr(o, name)
            elif (hasattr(o, name)):
                if name.endswith('_id'):
                    name = name[:len(name) - 3:]
                if inspect(o.__class__).relationships[name].uselist:
                    field.data = [str(i.id) for i in getattr(o, name)]
                elif getattr(o, name) is not None:
                    field.data = str(getattr(o, name).id)

    def load_default_data(self, session: SessionBase, cls):
        ''' Загружает в форму данные, которые помечены как значения по умолчанию для объектов перечислений '''
        rels = inspect(cls).relationships.keys()
        simple_attrs = inspect(cls).column_attrs.keys()
        for name, field in self._fields.items():
            if name.endswith('_id'):
                name = name[:len(name) - 3:]
            if name in rels and hasattr(inspect(cls).relationships[name].entity.class_, 'is_default'):
                cls_entity = inspect(cls).relationships[name].entity.class_
                if inspect(cls).relationships[name].uselist:
                    field.data = [str(i.id) for i in session.scalars(sa.select(cls_entity).where(cls_entity.is_default==True)).all()]
                else:
                    try:
                        field.data = str(session.execute(sa.select(cls_entity.id).where(cls_entity.is_default==True)).one()[0])
                    except MultipleResultsFound:
                        field.data = str(session.execute(sa.select(cls_entity.id).where(cls_entity.is_default==True)).first()[0])
                    except NoResultFound:
                        field.data = str(session.execute(sa.select(cls_entity.id)).first()[0])
            elif name in simple_attrs:
                ins = inspect(cls).column_attrs[name].columns[0].default
                if ins is None:
                    continue
                elif not ins.is_callable:
                    # Если значение по умолчанию - простое, т. е. не вызывается
                    field.data = ins.arg
                else:
                    # Значение по умолчанию - фунция
                    try:
                        # Пытаемся вызвать значение по умолчанию без контекста.
                        field.data = ins.arg(None)
                    except Exception:
                        # Пропускаем все ошибки, которые могли возникнуть на этапе присваивания - это происходит вследствие отсутствия контекста (ctx = None).
                        #  Функция создания по умолчанию не должна зависеть от текущего контекста создания объекта
                        continue

    def load_data_from_json(self, args: dict) -> None:
        """ Load data, stored in dict to current form. """
        for field_name in self._fields:
            if field_name in args:
                try:
                    if self._fields[field_name].__class__.__name__ == 'DateField':
                        self._fields[field_name].data = datetime.datetime.fromtimestamp(float(args[field_name]), datetime.UTC)
                    else:
                        self._fields[field_name].data = args[field_name]
                except ValueError:
                    abort(400)
    
    def render_script(self) -> Markup:
        """ render all scripts, that assigned to field in <script> tags """
        script_list = []
        for name, field in self._fields.items():
            if hasattr(field, 'script_tag'):
                script_list.append(field.script_tag)
        if len(script_list) == 0:
            return Markup('')
        return Markup('\n'.join(['<script>' + i + '</script>' for i in script_list]))

class WysiwygWidget(widgets.TextArea):
    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' wysiwyg'
        else:
            kwargs.setdefault('class', 'wysiwyg')
        return super(WysiwygWidget, self).__call__(field, **kwargs)


class WysiwygField(fields.TextAreaField):
    def __init__(self, *args, **kwargs):
        super(WysiwygField, self).__init__(*args, **kwargs)
        side_libraries.library_required('ckeditor')
    widget = WysiwygWidget()


class IerarchicalStructure:
    def __init__(self, attrs, is_same_type=False): # attrs = [(value, label, selected)]
        if len(attrs) != 0:
            cls_1 = attrs[0][1].__class__
            for i in attrs[1:]:
                if i[1].__class__ != cls_1:
                    raise ValueError("All objects must have such class!")
        self.attrs = attrs # Изначальный список. Представляет из себя список [(value, label, selected)], где value - это id, label - это сам объект, а selected- выбран ли этот объект
        self.is_same_type = is_same_type

    def to_json(self):

        def horisontal_convert(lst):
            ''' Преобразует начальный список вида [(val, label, selected)] к списку вида [{name: заголовок_объекта, value: id_объекта, children: [подобъекты]}],
            выполняет данное преобразование только для текущих объектов, т.е. группируя текущие объекты по их родителю.'''
            res = []
            max_id = int(max(lst, key=lambda x: int(x[0]))[0])
            while (len(lst) != 0):
                obj = lst[0][1]
                max_id += 1
                if hasattr(obj.__class__, 'parent') and callable(getattr(obj.__class__, 'parent')) and obj.parent() is not None:
                    cond = lambda x: hasattr(x[1].__class__, 'parent') and x[1].parent() is not None and x[1].parent().id==obj.parent().id
                    childs = list(filter(cond, lst))
                    if not (self.is_same_type):
                        res += [{'obj': obj.parent(), 'name': str(obj.parent().treeselecttitle), 'value': str(max_id), 'children': [{'name': str(i[1].treeselecttitle), 'value': i[0], 'children': []} for i in childs]}]
                    else:
                        res += [{'obj': obj.parent(), 'name': str(obj.parent().treeselecttitle), 'value': str(obj.parent().id), 'children': [{'name': str(i[1].treeselecttitle), 'value': i[0], 'children': []} for i in childs]}]
                    new_lst = list(filter(lambda x: not cond(x), lst))
                    lst = new_lst
                else:
                    res += [{'name': str(obj.treeselecttitle), 'value': str(obj.id), 'children': []}]
                    new_lst = lst[1::]
                    lst = new_lst
            return res

        def vertical_convert(lst):
            ''' Дальнейшее преобразование. Данный список объектов рекурсивно группирует по их родителям до тех пор, пока есть родительские объекты '''
            res = []
            max_id = int(max(lst, key=lambda x: int(x['value']))['value'])
            changed = False
            while (len(lst) != 0):
                if 'obj' in lst[0]:
                    changed = True
                    obj = lst[0]['obj']
                else:
                    e = lst[0]
                    res.append(e)
                    lst = lst[1::]
                    continue
                max_id += 1
                if hasattr(obj.__class__, 'parent') and callable(getattr(obj.__class__, 'parent')) and obj.parent() != None:
                    cond = lambda x: 'obj' in x and hasattr(x['obj'].__class__, 'parent') and x['obj'].parent().id==obj.parent().id
                    childs = list(filter(cond, lst))
                    if not (self.is_same_type):
                        res += [{'obj': obj.parent(), 'name': str(obj.parent().treeselecttitle), 'value': str(max_id), 'children': [{'name': i['name'], 'value': i['value'], 'children': i['children']} for i in childs]}]
                    else:
                        res += [{'obj': obj.parent(), 'name': str(obj.parent().treeselecttitle), 'value': str(obj.parent().id), 'children': [{'name': i['name'], 'value': i['value'], 'children': i['children']} for i in childs]}]
                    new_lst = list(filter(lambda x: not cond(x), lst))
                    lst = new_lst
                else:
                    e = lst[0]
                    e.pop('obj')
                    res.append(e)
                    lst = lst[1::]
            if changed:
                return vertical_convert(res)
            return res

        if len(self.attrs) != 0:
            lst = vertical_convert(horisontal_convert(self.attrs))
        else:
            lst = []
        return json.dumps(lst)


class TreeSelectMultipleWidget(widgets.Select):
    def __init__(self, *args, **kwargs):
        super(TreeSelectMultipleWidget, self).__init__(*args, **kwargs)
        self.multiple = True

    def __call__(self, field, **kwargs):
        res = super(TreeSelectMultipleWidget, self).__call__(field, style="display: none", **kwargs)
        res = str(res)
        choices = IerarchicalStructure([(val, label, selected) for val, label, selected, _ in field.iter_choices()])
        js_list_choices = choices.to_json()
        selected = [val for val, label, selected, _ in field.iter_choices() if selected]
        treeselect_name = 'treeselect_' + str(field.name)
        res += r'<div class="'+ 'treeselect__' + field.name + r'''"></div>'''
        script = '''const treeselect__''' + field.name + r'''domElement = document.querySelector('.''' + 'treeselect__' + field.name + r'''')
        const ''' + treeselect_name + ''' = new Treeselect({
        parentHtmlContainer: treeselect__''' + field.name + '''domElement,
        value: JSON.parse("''' + str(escapejs(json.dumps(selected))) + r'''"),
        options: JSON.parse("''' + str(escapejs(js_list_choices)) + r'''"),
        })
        ''' + treeselect_name + '''.srcElement.addEventListener('input', (e) => {
        var dnd = document.querySelector('#''' + str(field.id) + '''');
        var selected = e.detail;
        Array.from(dnd.options).forEach(function (option) {
            if (selected.includes(option.value)) {
                option.selected = true;
            } else {
                option.selected = false;
            }
        });
        })'''
        field.script_tag = script
        side_libraries.require_script(script)
        return Markup(res)


class TreeSelectSingleWidget(widgets.Select):
    def __init__(self, *args, **kwargs):
        super(TreeSelectSingleWidget, self).__init__(*args, **kwargs)
        self.multiple = False

    def __call__(self, field, **kwargs):
        res = super(TreeSelectSingleWidget, self).__call__(field, style="display: none", **kwargs)
        if not hasattr(field, 'disabledBranchNode'):
            field.disabledBranchNode = True
        if not hasattr(field, 'is_same_type'):
            field.is_same_type = False
        dbn = str(field.disabledBranchNode).lower()
        res = str(res)
        if len(list(field.iter_choices())) == 0 or len(list(field.iter_choices())) <= 1 and list(field.iter_choices())[0][0] == '0':
            js_list_choices = '[]'
        else:
            if field.choices[0][0] == '0':
                field.choices = field.choices[1::]
            choices = IerarchicalStructure([(val, label, selected) for val, label, selected, _ in field.iter_choices()], is_same_type=field.is_same_type)
            js_list_choices = choices.to_json()
        selected = [val for val, label, selected, _ in field.iter_choices() if selected]
        if len(selected) >= 1:
            selected = selected[0]
        else:
            selected = None
        treeselect_name = 'treeselect_' + str(field.name)
        res += r'<div class="'+ 'treeselect__' + field.name + r'''"></div>'''
        script = '''const treeselect__''' + field.name + r'''domElement = document.querySelector('.''' + 'treeselect__' + field.name + r'''')
        const ''' + treeselect_name + ''' = new Treeselect({
        parentHtmlContainer: treeselect__''' + field.name + r'''domElement,''' + '\n'
        if selected is not None:
            script += r'''value: JSON.parse("''' + str(escapejs(json.dumps(selected))) + '"),\n'
        script += r'''options: JSON.parse("''' + str(escapejs(js_list_choices)) + r'''"),
        isSingleSelect: true,
        disabledBranchNode: ''' + dbn + ''',
        })
        ''' + treeselect_name + '''.srcElement.addEventListener('input', (e) => {
        var dnd = document.querySelector('#''' + str(field.id) + '''');
        dnd.value = e.detail;
        })'''
        field.script_tag = script
        side_libraries.require_script(script)
        return Markup(res)


class TreeSelectMultipleField(fields.SelectMultipleField):
    def __init__(self, *args, **kwargs):
        super(TreeSelectMultipleField, self).__init__(*args, **kwargs)
        side_libraries.library_required('treeselectjs')
    widget = TreeSelectMultipleWidget()


class TreeSelectSingleField(fields.SelectField):
    def __init__(self, *args, **kwargs):
        super(TreeSelectSingleField, self).__init__(*args, **kwargs)
        side_libraries.library_required('treeselectjs')
    widget = TreeSelectSingleWidget()


class PickrColorWidget(widgets.TextInput):
    def __call__(self, field, **kwargs):
        pickr_id = random_string(20)
        if not field.data:
            field.data = "rgba(0, 0, 0, 1)"
        res = super(PickrColorWidget, self).__call__(field, style="display: none", **kwargs)
        res = str(res)
        res += '''<div id="''' + str(pickr_id) + '''"></div>'''
        script = '''const pickr_''' + str(pickr_id) + ''' = Pickr.create(''' + r'''{
            el: "#''' + str(pickr_id)  + '''",
            theme: 'classic',
            comparison: false,
            showAlways: false,
            default: "''' + str(field.data) + '''",

            swatches: ['rgba(244, 67, 54, 1)', 'rgba(233, 30, 99, 0.95)', 'rgba(156, 39, 176, 0.9)', 'rgba(103, 58, 183, 0.85)', 'rgba(63, 81, 181, 0.8)', 'rgba(33, 150, 243, 0.75)','rgba(3, 169, 244, 0.7)','rgba(0, 188, 212, 0.7)','rgba(0, 150, 136, 0.75)', 'rgba(76, 175, 80, 0.8)', 'rgba(139, 195, 74, 0.85)', 'rgba(205, 220, 57, 0.9)','rgba(255, 235, 59, 0.95)', 'rgba(255, 193, 7, 1)'],
            components: {
                preview: true,
                opacity: true,
                hue: true,
                interaction: {hex: true, rgba: true, hsla: true, hsva: true, cmyk: true, input: true, clear: true, save: true }
            }
        });
        pickr_''' + str(pickr_id) + '''.on('save', instance => {
            if (instance != null) {
            document.getElementById("''' + str(field.id) + '''").setAttribute("value", instance.toRGBA().toString(3));
            }
            else { document.getElementById("''' + str(field.id) + '''").setAttribute("value", "") }
            pickr_''' + str(pickr_id) + '''.hide();})</script>'''
        field.script_tag = script
        side_libraries.require_script(script)
        return Markup(res)


class PickrColorField(fields.StringField):
    def __init__(self, *args, **kwargs):
        super(PickrColorField, self).__init__(*args, **kwargs)
        side_libraries.library_required('pickr')
    widget = PickrColorWidget()


class Select2Widget:
    def __init__(self, multiple=False):
        self.multiple = multiple
    
    def __call__(self, field, locale: str='EN', callback: Optional[str]=None, dropdownParent: Optional[str]=None, **kwargs) -> Markup:
        if field.data:
            try:
                if not self.multiple:
                    field_val = getattr(db.session.scalars(sa.select(field.object_class).where(field.object_class.id==int(field.data))).one(), field.attr_title)
                    field_data = f'<option value="{field.data}" selected="selected">{field_val}</option>'
                else:
                    field_data = ''
                    for e in db.session.scalars(sa.select(field.object_class).where(field.object_class.id.in_([int(k) for k in field.data]))):
                        field_data += f'<option value="{e.id}" selected="selected">{getattr(e, field.attr_title)}</option>\n'
            except (MultipleResultsFound, NoResultFound, ValueError, TypeError):
                field_data = ''
        else:
            field_data = ''
        if callback is None:
            if field.object_class is None:
                raise ValueError("Object class of Select2Field cannot being None when callback is None")
            callback = url_for('generic.enumeration_object_list', object_class=field.object_class.__name__)
        if 'class' in kwargs:
            additional_classes = " " + kwargs['class']
        else:
            additional_classes = ''
        if not self.multiple:
            select_field = f'<select class="select2-standard-widget{additional_classes}" id="{field.id}" name="{field.name}">{field_data}</select>'
        else:
            select_field = f'<select class="select2-standard-widget{additional_classes}" id="{field.id}" name="{field.name}" multiple>{field_data}</select>'
        jquery_script = '$(document).ready(function() { $("#' + field.id + '").select2({ language: "' + locale + '", placeholder: "' + _l("Select an option") + '", '
        if self.multiple:
            jquery_script += '\ncloseOnSelect: false, '
        if callback is not None:
            jquery_script += "\nallowClear: true,"
        if dropdownParent is not None:
            jquery_script += f'\ndropdownParent: $("#{dropdownParent}"),'
        jquery_script += '''ajax: {
            url: "''' + callback + '''",'''
        jquery_script += '''
        dataType: 'json',
        } })})'''
        field.script_tag = jquery_script
        side_libraries.require_script(jquery_script)
        return Markup(select_field)


class Select2Field(SelectField):
    widget = Select2Widget()
    def __init__(self, object_class, label=None, validators=None, coerce=int, choices=None, validate_choice=True, callback=None, locale='EN', attr_title='title', **kwargs):
        super().__init__(label, validators, coerce, choices, validate_choice, **kwargs)
        self.object_class = object_class
        self.callback = callback
        self.locale = locale
        self.attr_title = attr_title
        side_libraries.library_required('select2')

    def pre_validate(self, form):
        if not self.validate_choice:
            return

        try:
            db.session.scalars(sa.select(self.object_class.id).where(self.object_class.id == self.coerce(self.data))).one()
        except (MultipleResultsFound, NoResultFound, ValueError, TypeError):
            raise ValidationError(self.gettext("Not a valid choice."))
    
    def __call__(self, *args, **kwargs) -> Markup:
        return super().__call__(*args, locale=self.locale, callback=self.callback, **kwargs)


class Select2MultipleField(SelectMultipleField):
    widget = Select2Widget(multiple=True)
    def __init__(self, object_class, label=None, validators=None, coerce: Callable=int, choices=None, validate_choice: bool=True, callback: Optional[str]=None, locale: str='EN',
                 attr_title: str='title', validate_funcs: Callable=None, **kwargs):
        super().__init__(label, validators, coerce, choices, validate_choice, **kwargs)
        self.object_class = object_class
        self.callback = callback
        self.locale = locale
        self.attr_title = attr_title
        self.validate_funcs = validate_funcs
        side_libraries.library_required('select2')
    
    def pre_validate(self, form):
        if not self.validate_choice:
            return
        
        if self.validate_funcs is None:
            try:
                if not db.session.scalars(sa.select(sa.func.count(self.object_class.id)).where(self.object_class.id.in_([self.coerce(i) for i in self.data]))).one() == len(self.data):
                    raise ValidationError(self.gettext("Not a valid choice."))
            except (MultipleResultsFound, NoResultFound, ValueError, TypeError):
                raise ValidationError(self.gettext("Not a valid choice."))
        else:
            self.validate_funcs(self)
    
    def __call__(self, *args, **kwargs) -> Markup:
        return super().__call__(*args, locale=self.locale, callback=self.callback, **kwargs)


class ProgressBarWidget(widgets.NumberInput):
    def __init__(self, step=None, min=None, max=None):
        self.step = step
        self.min = min
        self.max = max

    def __call__(self, field, **kwargs) -> Markup:
        if self.step is not None:
            kwargs.setdefault("step", self.step)
        else:
            kwargs.setdefault("step", field.step)
        if self.min is not None:
            kwargs.setdefault("min", self.min)
        else:
            kwargs.setdefault("min", field.min_value)
        if self.max is not None:
            kwargs.setdefault("max", self.max)
        else:
            kwargs.setdefault("max", field.max_value)
        kwargs.setdefault('style', 'display: none')
        fst_result = super().__call__(field, **kwargs)
        params = {'step': kwargs['step'], 'min': kwargs['min'], 'max': kwargs['max'], 'width': '100%',
                  'design': field.design, 'showMinMaxLabel': field.showMinMaxLabel, 'showCurrentValueLabel': field.showCurrentValueLabel, 'labelsPosition': field.labelPosition,
                  'popup': field.popup, 'theme': field.theme, 'handle': field.handle, 'size': field.size}
        if field.data:
            params['value'] = field.data
        if field.unit:
            params['unit'] = field.unit
        range_slider_id = random_string(20)
        div = f'<div id="range_slider_{range_slider_id}"></div>'
        func = '''function(val) {
        ''' + f'document.getElementById("{field.id}").setAttribute("value", val)' + '''
        }'''
        script = f'let obj_range_slider_{range_slider_id}_data = {json.dumps(params)};obj_range_slider_{range_slider_id}_data.onfinish = {func};' + '''
        new RangeSlider(document.getElementById("range_slider_''' + range_slider_id + '"), obj_range_slider_' + range_slider_id + '''_data );'''
        field.script_tag = script
        side_libraries.require_script(script)
        return Markup(str(fst_result) + div)


class ProgressBarField(fields.IntegerField):
    widget = ProgressBarWidget()

    def __init__(self, min_value: int=0, max_value: int=100, step: int=1, unit: Optional[str]=None, design: str='3d',
                 showMinMaxLabel: bool=True, showCurrentValueLabel: bool=True, labelPosition: str='bottom',
                  popup: str='bottom', theme: str='positive', handle: str='round', size: str='small', label=None, validators=None, **kwargs):
        self.min_value = int(min_value)
        self.max_value = int(max_value)
        self.step = int(step)
        self.unit = unit
        self.design = design
        self.showMinMaxLabel = showMinMaxLabel
        self.showCurrentValueLabel = showCurrentValueLabel
        self.labelPosition = labelPosition
        self.popup = popup
        self.theme = theme
        self.handle = handle
        self.size = size
        if 'default' not in kwargs:
            kwargs['default'] = min_value
        super().__init__(label, validators, **kwargs)
        side_libraries.library_required('range_slider')
    
    def _value(self) -> str:
        if self.raw_data:
            return self.raw_data[0]
        if self.data is not None:
            return str(self.data)
        return str(self.min_value)
    
    def pre_validate(self, form):
        try:
            data = int(self.data)
        except (ValueError, TypeError):
            raise ValidationError("Not a valid value")
        if data < self.min_value or data > self.max_value:
            raise ValidationError("Not a valid value")
        return super().pre_validate(form)


class Select2IconWidget:
    def __init__(self, multiple=False):
        self.multiple = multiple
    
    def __call__(self, field, locale: str='EN', dropdownParent: Optional[str]=None, **kwargs) -> Markup:
        field_data = ''
        if field.data: # field.data: int | List[int]
            try:
                if not self.multiple:
                    object_element = db.session.scalars(sa.select(field.object_class).where(field.object_class.id==int(field.data))).one()
                    field_title = getattr(object_element, field.attr_title)
                    icon_value = getattr(object_element, field.attr_icon)
                    color_value = getattr(object_element, field.attr_color, "")
                    field_data = f'<option value="{field.data}" data-icon="{icon_value}" data-icon-color="{color_value}" selected="selected">{field_title}</option>'
                else:
                    field_data = ''
                    for e in db.session.scalars(sa.select(field.object_class).where(field.object_class.id.in_([int(k) for k in field.data]))):
                        field_title = getattr(e, field.attr_title)
                        icon_value = getattr(e, field.attr_icon)
                        color_value = getattr(e, field.attr_color)
                        field_data += f'<option value="{e.id}" data-icon="{icon_value}" data-icon-color="{color_value}" selected="selected">{field_title}</option>\n'
            except (ValueError, TypeError):
                field_data = ''
        if isinstance(field.choices, (list, tuple)):
            for choice in field.choices: # choice: List[Tuple[int, Any]] - список объектов, имеющих атрибуты id, icon и title
                if isinstance(choice[1], field.object_class):
                    if (self.multiple and field.data and str(choice[1].id) in field.data) or (not self.multiple and str(choice[1].id) == field.data):
                        continue
                    field_data += f'<option value="{choice[1].id}" data-icon="{getattr(choice[1], field.attr_icon)}" data-icon-color="{getattr(choice[1], field.attr_color, "")}">{getattr(choice[1], field.attr_title)}</option>\n'
                else:
                    field_data += f'<option value="{choice[0]}" data-icon="" data-icon-color="">{choice[1]}</option>\n'
        additional_classes = ''
        if 'class' in kwargs:
            additional_classes = " " + kwargs['class']
        if not self.multiple:
            select_field = f'<select class="select2-standard-widget{additional_classes}" id="{field.id}" name="{field.name}">{field_data}</select>'
        else:
            select_field = f'<select class="select2-standard-widget{additional_classes}" id="{field.id}" name="{field.name}" multiple>{field_data}</select>'
        jquery_script = '''$(document).ready(function() { $("#''' + str(field.id) + '''").select2({ language: "''' + locale + '''", placeholder: "''' + _l("Select an option") + '''", allowClear: true,'''
        if self.multiple:
            jquery_script += '\ncloseOnSelect: false, '
        if dropdownParent is not None:
            jquery_script += f'\ndropdownParent: $("#{dropdownParent}"),'
        if not self.multiple:
            jquery_script += 'selectionCssClass: "select2-single-icon-list-widget", width: "300px",'
        jquery_script += '''
        
          templateResult: function(state) { if (!state.id) {
          return state.text;
          }
          let icon = state.element.getAttribute('data-icon');
          let color = state.element.getAttribute('data-icon-color');
          if(icon !== null && color !== null) {
            return $('<span><i class="' + icon + '" style="color: ' + color + '"></i>' + state.text + '</span>')
          }
          else if (icon !== null) {
            return $('<span><i class="' + icon + '"></i>' + state.text + '</span>')
          } },
          templateSelection: function(state) { if (!state.id) {
          return state.text;
          }
          let icon = state.element.getAttribute('data-icon');
          let color = state.element.getAttribute('data-icon-color');
          if (icon !== null && color != null) {
           return $('<span class="select2-icon-field-element"><i class="' + icon + '" style="color: ' + color + '"></i></span>')
          } else if (icon !== null) {
            return $('<span class="select2-icon-field-element"><i class="' + icon + '"></i></span>')
          }
          },
           }) });
        '''
        if field.data in ["", None, []]:
            jquery_script += f'''$('#{field.id}').val(null).trigger("change")'''
        field.script_tag = jquery_script
        side_libraries.require_script(jquery_script)
        return Markup(select_field)


class Select2IconField(SelectField):
    widget = Select2IconWidget()
    def __init__(self, object_class: Any, label: str | None=None, validators: List=None, coerce: Callable[[str], Any]=int,
                 choices: List[Tuple[int, Any]] | None=None, validate_choice: bool=True, locale: str='EN',
                 attr_title: str='title', attr_icon: str="icon", attr_color: str="color", **kwargs):
        super().__init__(label, validators, coerce, choices, validate_choice, **kwargs)
        self.object_class = object_class
        self.locale = locale
        self.attr_title = attr_title
        self.attr_icon = attr_icon
        self.attr_color = attr_color
        side_libraries.library_required('select2')
    
    def _choices_generator(self, choices: List[Tuple[int, Any]]) -> Generator[Tuple[str, str, bool, dict]]:
        if not choices:
            _choices = []

        elif isinstance(choices[0], (list, tuple)):
            _choices = choices

        for choice in _choices:
            if self.data is not None:
                selected = choice[1].id == self.coerce(self.data)
            else:
                selected = False
            yield (choice[1].id, getattr(choice[1], self.attr_title), selected, {})

    def pre_validate(self, form):
        if not self.validate_choice:
            return

        for _, _, match, *_ in self.iter_choices():
            if match:
                break
        else:
            raise ValidationError(self.gettext('Not a valid choice'))
    
    
    def __call__(self, *args, **kwargs) -> Markup:
        return super().__call__(*args, locale=self.locale, **kwargs)


class Select2IconMultipleField(SelectMultipleField):
    widget = Select2IconWidget(multiple=True)

    def __init__(self, object_class: Any, label: str | None=None, validators: List=None, coerce: Callable[[str], Any]=int,
                 choices: List[Tuple[int, Any]] | None=None, validate_choice: bool=True, locale: str='EN',
                 attr_title: str='title', attr_icon: str="icon", attr_color: str="color", **kwargs):
        super().__init__(label, validators, coerce, choices, validate_choice, **kwargs)
        self.object_class = object_class
        self.locale = locale
        self.attr_title = attr_title
        self.attr_icon = attr_icon
        self.attr_color = attr_color
        side_libraries.library_required('select2')


class FontAwesomeIconComputedSymbolInput(widgets.HiddenInput):
    def __call__(self, field: wtforms.Field, **kwargs):
        hidden_result: Markup = super().__call__(field, **kwargs)
        javascript = f'''document.getElementById('{field.observable_field_id}').addEventListener('change', function() {{
        function faUnicode(name) {{
            var testI = document.createElement('i');
            var char;
            testI.className = name;
            document.body.appendChild(testI);
            char = window.getComputedStyle( testI, ':before' )
                    .content.replace(/'|"/g, '');
            testI.remove();
            return char.charCodeAt(0);
        }}
        current_unicode = faUnicode(this.value);
        if(current_unicode != 110) {{
            document.getElementById('{field.id}').value = faUnicode(this.value);
        }}
        else {{
            document.getElementById('{field.id}').value = 0;
        }}
        }});'''
        side_libraries.require_script(javascript)
        field.script_tag = javascript
        return hidden_result


class FontAwesomeIconField(wtforms.HiddenField):
    widget = FontAwesomeIconComputedSymbolInput()
    observable_field_id = "icon_class"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
