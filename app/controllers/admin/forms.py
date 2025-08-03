from app.controllers.forms import FlaskForm
from app import db
import wtforms
from wtforms.form import FormMeta
import wtforms.validators as validators
from sqlalchemy.inspection import inspect
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa


def validate_unique(form, field):
    # В дальнейшем написать валидацию уникальных объектов... достигается через inspect(ni).columns[1].unique
    pass


class ObjectFormMeta(FormMeta):
    def __new__(cls, name, bases, attrs):
        if 'obj' not in attrs:
            return super(ObjectFormMeta, cls).__new__(cls, name, bases, attrs)
        inspected_columns = []
        obj = attrs.get('obj')
        session = attrs.get('session')
        for col in inspect(obj).columns:
            if col.name == 'id' or col.name.endswith('_id') or ('on_form' in col.info and not col.info['on_form']):
                continue
            # Обработка валидаторов
            valids = []
            if not col.nullable and not (col.type.__class__.__name__ == 'Boolean'):
                valids.append(validators.DataRequired(message=_l("This field is mandatory!")))
            if col.type.__class__.__name__ == 'String' and col.type.length is not None:
                valids.append(validators.length(max=col.type.length, message=_l('This field must not exceed %(length)s characters in length', length=col.type.length)))
            if col.unique:
                validate_name = 'validate_' + col.name
                def validate_func(form, field):
                    another_object = db.session.scalars(sa.select(obj).where(getattr(obj, col.name) == field.data.strip())).first()
                    if hasattr(form, 'current_object_value') and form.current_object_value is not None and getattr(form.current_object_value, col.name) == field.data:
                        return None
                    if another_object is not None:
                        raise validators.ValidationError(_l("Object with specified field value already exist in database"))
                attrs.update({validate_name: validate_func})
            # Обработка полей
            if 'form' in col.info:
                nf = col.info['form'](_l("%(field_name)s:", field_name=col.info['label']), validators=valids)
            elif col.type.__class__.__name__ == 'String' or col.type.__class__.__name__ == 'LimitedLengthString':
                nf = wtforms.StringField(_l("%(field_name)s:", field_name=col.info['label']), validators=valids)
            elif col.type.__class__.__name__ == 'Integer':
                nf = wtforms.fields.IntegerField(_l("%(field_name)s:", field_name=col.info['label']), validators=valids)
            elif col.type.__class__.__name__ == 'Float':
                nf = wtforms.FloatField(_l("%(field_name)s:", field_name=col.info['label']), validators=valids)
            elif col.type.__class__.__name__ == 'DateTime':
                nf = wtforms.DateField(_l("%(field_name)s:", field_name=col.info['label']), validators=valids)
            elif col.type.__class__.__name__ == 'Boolean':
                nf = wtforms.BooleanField(_l("%(field_name)s:", field_name=col.info['label']), validators=valids)
            if 'description' in col.info:
                nf.description = col.info['description']
            attrs.update({col.name: nf})
            inspected_columns.append(col.name)
        for rel_name, rel in inspect(obj).relationships.items():
            if 'on_form' in rel.info and not rel.info['on_form']:
                continue
            if not rel.uselist:
                # Это простая ссылка - т. е. не список. Тогда создаём простой SelectField:
                choices = [('0', '')] + session.execute(db.select(rel.entity.class_.id, rel.entity.class_.title)).all()
                nf = wtforms.SelectField(_l("%(field_name)s:", field_name=rel.info['label']), choices=choices)
            else:
                choices = session.execute(db.select(rel.entity.class_.id, rel.entity.class_.title)).all()
                nf = wtforms.SelectMultipleField(_l("%(field_name)s:", field_name=rel.info['label']), choices=[(str(i[0]), str(i[1])) for i in choices])
            if 'description' in rel.info:
                nf.description = rel.info['description']
            attrs.update({rel_name: nf})
            inspected_columns.append(rel_name)
        instance = super(ObjectFormMeta, cls).__new__(cls, name, bases, attrs)
        instance.inspected_columns = inspected_columns
        return instance


class ObjectForm(FlaskForm, metaclass=ObjectFormMeta):
    def __init__(self, current_object_value=None, *args, **kwargs):
        super(ObjectForm, self).__init__(*args, **kwargs)
        self.current_object_value = current_object_value


def get_object_create_form(obj, session):
    return type('ObjectCreateForm', (ObjectForm,), {'obj': obj, 'session': session, 'submit': wtforms.SubmitField(_l("Create"))})


def get_object_edit_form(obj, session):
    return type('ObjectEditForm', (ObjectForm, ), {'obj': obj, 'session': session,
                                                   'submit': wtforms.SubmitField(_l("Save")),
                                                   'id': wtforms.HiddenField(validators=[validators.DataRequired()])})


class StatusTransitsFormMeta(FormMeta):
    def __new__(cls, name, bases, attrs):
        if 'obj' not in attrs:
            return super(StatusTransitsFormMeta, cls).__new__(cls, name, bases, attrs)
        obj = attrs.get('obj')
        session = attrs.get('session')
        all_objs = session.scalars(db.select(obj)).all()
        attr_names = []
        for i in all_objs:
            name_lst = []
            for j in all_objs:
                now_name = f'switch_{i.id}_{j.id}'
                name_lst.append(now_name)
                if i.id == j.id:
                    nf = wtforms.BooleanField(_l('Transition from %(i_title)s to %(j_title)s:', i_title=i.title, j_title=j.title), render_kw={'disabled': True})
                else:
                    nf = wtforms.BooleanField(_l('Transition from %(i_title)s to %(j_title)s:', i_title=i.title, j_title=j.title))
                attrs.update({now_name: nf})
            attr_names.append(name_lst)
        instance = super(StatusTransitsFormMeta, cls).__new__(cls, name, bases, attrs)
        instance.attr_names = attr_names
        instance.all_objs = all_objs
        return instance


class StatusTransitForm(FlaskForm, metaclass=StatusTransitsFormMeta):
    def load_exist_statuses(self):
        for now_line in self.attr_names:
            for now_attr_name in now_line:
                _, from_id, to_id = now_attr_name.split('_')
                current_field = getattr(self, now_attr_name)
                current_object = self.session.get(self.obj, from_id)
                to_object = self.session.get(self.obj, to_id)
                current_field.data = to_object in current_object.can_switch_to_state or to_object.id == current_object.id

    def populate_statuses(self):
        for now_line in self.attr_names:
            for now_attr_name in now_line:
                _, from_id, to_id = now_attr_name.split('_')
                current_object = self.session.get(self.obj, from_id)
                to_object = self.session.get(self.obj, to_id)
                current_field = getattr(self, now_attr_name)
                if current_field.data:
                    current_object.can_switch_to_state.add(to_object)
                else:
                    if to_object in current_object.can_switch_to_state:
                        current_object.can_switch_to_state.remove(to_object)


def get_status_transit_form(obj, session):
    return type('StatusTransitForm', (StatusTransitForm,), {'obj': obj,
                                                            'session': session,
                                                            'submit': wtforms.SubmitField(_l("Save"))})
