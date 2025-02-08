from app.controllers.forms import FlaskForm
from app import db
from app.models import ProjectRole, RoleHasProjectObjectAction
import wtforms
import wtforms.validators as validators
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa
from wtforms.form import FormMeta
from app.helpers.admin_helpers import get_all_project_objects
from typing import List


class ProjectRoleForm(FlaskForm):
    title = wtforms.StringField(_l("%(field_name)s:", field_name=ProjectRole.title.info["label"]),
                                validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=ProjectRole.title.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(ProjectRole.title.type.length)))])
    description = wtforms.TextAreaField(_l("%(field_name)s:", field_name=ProjectRole.description.info["label"]), validators=[validators.Optional()])


class ProjectRoleCreateForm(ProjectRoleForm):
    string_slug = wtforms.StringField(_l("%(field_name)s:", field_name=ProjectRole.string_slug.info["label"]),
                                validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=ProjectRole.string_slug.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(ProjectRole.string_slug.type.length)))])
    submit = wtforms.SubmitField(_l("Create"))
    
    def validate_string_slug(form, field):
        r = db.session.scalars(sa.select(ProjectRole).where(ProjectRole.string_slug == field.data)).first()
        if r is not None:
            raise wtforms.ValidationError(_l("This Slug is already exist!"))


class ProjectRoleEditForm(ProjectRoleForm):
    submit = wtforms.SubmitField(_l("Save"))


class ProjectRolePermissionFormMeta(FormMeta):
    def __new__(cls, name, bases, attrs):
        if 'all_roles' not in attrs:
            return super(ProjectRolePermissionFormMeta, cls).__new__(cls, name, bases, attrs)
        attr_names = []
        for role in attrs.get('all_roles'):
            role_name_lst = []
            for o in get_all_project_objects():
                name_lst = []
                for a in o.Meta.project_permission_actions.keys():
                    ra = db.session.scalars(sa.select(RoleHasProjectObjectAction).where(db.and_(RoleHasProjectObjectAction.role_id == role.id,
                                                                                                    RoleHasProjectObjectAction.object_class_name == o.__name__,
                                                                                                    RoleHasProjectObjectAction.action == a))).first()
                    if ra is None:
                        ra = RoleHasProjectObjectAction(role_id=role.id, object_class_name=o.__name__, action=a, is_granted=False)
                        db.session.add(ra)
                        db.session.commit()
                    role_name = 'role_' + str(role.id) 
                    now_name = role_name + '____' + o.__name__ + '____' + a
                    nf = wtforms.BooleanField(_l("%(action_name)s:", action_name=o.Meta.project_permission_actions[a]), default=ra.is_granted)
                    attrs.update({now_name: nf})
                    name_lst.append(now_name)
                role_name_lst.append(name_lst)
            attr_names.append(role_name_lst)
        instance = super(ProjectRolePermissionFormMeta, cls).__new__(cls, name, bases, attrs)
        instance.attr_names = attr_names
        instance.project_role = role
        return instance


class ProjectRolePermissionForm(FlaskForm, metaclass=ProjectRolePermissionFormMeta):
    def populate_permissions(self):
        for line_roles in self.attr_names:
            for line_objects in line_roles:
                for now_attr_name in line_objects:
                    role_name, object_class_name, action = now_attr_name.split('____')
                    role_id = int(role_name[5::])
                    current_field = getattr(self, now_attr_name)
                    ra = db.session.scalars(sa.select(RoleHasProjectObjectAction).where(RoleHasProjectObjectAction.role_id == role_id,
                                                                                             RoleHasProjectObjectAction.object_class_name == object_class_name,
                                                                                             RoleHasProjectObjectAction.action == action)).first()
                    if ra is None:
                        ra = RoleHasProjectObjectAction(role_id=role_id, object_class_name=object_class_name, action=action)
                        db.session.add(ra)
                    ra.is_granted = current_field.data == True


def get_project_role_permission_form(all_roles: List[ProjectRole]) -> ProjectRolePermissionForm:
    return type('ProjectRolePermissionForm', (ProjectRolePermissionForm,), {'all_roles': all_roles,
                                                                            'submit': wtforms.SubmitField(_l("Save"))})