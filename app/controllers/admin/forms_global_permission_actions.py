from app.controllers.forms import FlaskForm
import wtforms
from wtforms.form import FormMeta
import wtforms.validators as validators
from flask_babel import lazy_gettext as _l
from app import db
import app.models as models
from app.helpers.general_helpers import get_global_objects_with_permissions
import sqlalchemy as sa
from typing import List


class UserPositionForm(FlaskForm):
    def __init__(self, position=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.position = position
    string_slug = wtforms.StringField(_l("%(field_name)s:", field_name=models.UserPosition.string_slug.info["label"]),
                                validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=models.UserPosition.string_slug.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(models.UserPosition.string_slug.type.length)))])
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.UserPosition.title.info["label"]),
                                validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=models.UserPosition.title.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(models.UserPosition.title.type.length)))])
    is_default = wtforms.BooleanField(_l("%(field_name)s:", field_name=models.UserPosition.is_default.info["label"]),
                                validators=[validators.Optional()])
    is_administrator = wtforms.BooleanField(_l("%(field_name)s:", field_name=models.UserPosition.is_administrator.info["label"]),
                                validators=[validators.Optional()])
    
    def validate_string_slug(form, field):
        if form.position is not None and field.data == form.position.string_slug:
            return None
        r = db.session.scalars(sa.select(models.UserPosition).where(models.UserPosition.string_slug == field.data)).first()
        if r is not None:
            raise wtforms.ValidationError(_l("This Slug is already exist!"))


class UserPositionFormCreate(UserPositionForm):
    submit = wtforms.SubmitField(_l("Create"))


class UserPositionFormEdit(UserPositionForm):
    submit = wtforms.SubmitField(_l("Edit"))


class GlobalRolePermissionFormMeta(FormMeta):
    def __new__(cls, name, bases, attrs):
        if 'positions' not in attrs:
            return super(GlobalRolePermissionFormMeta, cls).__new__(cls, name, bases, attrs)
        attr_names = []
        for position in attrs.get("positions"):
            position_name_lst = []
            for o in get_global_objects_with_permissions():
                name_lst = []
                for a in o.Meta.global_permission_actions.keys():
                    ua = db.session.scalars(sa.select(models.UserPositionHasObjectAction).where(db.and_(models.UserPositionHasObjectAction.position_id == position.id,
                                                                                                    models.UserPositionHasObjectAction.object_class_name == o.__name__,
                                                                                                    models.UserPositionHasObjectAction.action == a))).first()
                    if ua is None:
                        ua = models.UserPositionHasObjectAction(position_id=position.id, object_class_name=o.__name__, action=a, is_granted=False)
                        db.session.add(ua)
                    position_name = 'position_' + str(position.id) 
                    now_name = position_name + '____' + o.__name__ + '____' + a
                    nf = wtforms.BooleanField(_l("%(action_name)s:", action_name=o.Meta.global_permission_actions[a]), default=ua.is_granted)
                    attrs.update({now_name: nf})
                    name_lst.append(now_name)
                position_name_lst.append(name_lst)
            attr_names.append(position_name_lst)
        db.session.commit()
        instance = super(GlobalRolePermissionFormMeta, cls).__new__(cls, name, bases, attrs)
        instance.attr_names = attr_names
        return instance


class GlobalRolePermissionForm(FlaskForm, metaclass=GlobalRolePermissionFormMeta):
    def populate_permissions(self):
        for line_positions in self.attr_names:
            for line_objects in line_positions:
                for now_attr_name in line_objects:
                    position_name, object_class_name, action = now_attr_name.split('____')
                    position_id = int(position_name[9::])
                    current_field = getattr(self, now_attr_name)
                    ua = db.session.scalars(sa.select(models.UserPositionHasObjectAction).where(models.UserPositionHasObjectAction.position_id == position_id,
                                                                                                models.UserPositionHasObjectAction.object_class_name == object_class_name,
                                                                                                models.UserPositionHasObjectAction.action == action)).first()
                    if ua is None:
                        ua = models.UserPositionHasObjectAction(position_id=position_id, object_class_name=object_class_name, action=action)
                        db.session.add(ua)
                    ua.is_granted = current_field.data == True


def get_project_role_permission_form(positions: List[models.UserPosition]) -> GlobalRolePermissionForm:
    return type('GlobalRolePermissionForm', (GlobalRolePermissionForm,), {'positions': positions,
                                                                            'submit': wtforms.SubmitField(_l("Save"))})