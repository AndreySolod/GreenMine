from app import db, sanitizer
import app.models as models
from app.controllers.forms import FlaskForm, WysiwygField, TreeSelectMultipleField
import wtforms
import wtforms.validators as validators
from wtforms.form import FormMeta
from app.helpers.general_helpers import utcnow
from app.models import User, Project, ProjectRole, UserRoleHasProject
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa
from flask_login import current_user


class ProjectForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        leader_choices = [(u.id, u.title) for u in db.session.execute(sa.select(User.id, User.title).order_by(User.title))]
        self.leader.choices = leader_choices
    title = wtforms.StringField(_l("%(field_name)s:", field_name=Project.title.info["label"]), validators=[
                                validators.DataRequired(message=_l("This field is mandatory!")),
                                validators.Length(max=Project.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=Project.title.type.length))])
    start_at = wtforms.DateField(_l("%(field_name)s:", field_name=Project.start_at.info["label"]), validators=[
                                 validators.DataRequired(message=_l("This field is mandatory!"))], default=utcnow)
    end_at = wtforms.DateField(_l("%(field_name)s:", field_name=Project.end_at.info["label"]), validators=[
                               validators.DataRequired(message=_l("This field is mandatory!"))])
    description = WysiwygField(_l("%(field_name)s:", field_name=Project.description.info["label"]), validators=[
                               validators.DataRequired(message=_l("This field is mandatory!"))])
    leader = wtforms.SelectField(_l("%(field_name)s:", field_name=Project.leader.info["label"]),
                                 validators=[validators.DataRequired(message=_l("This field is mandatory!"))])

    def validate_end_at(form, field):
        if field.data < form.start_at.data:
            raise validators.ValidationError(_l("The planned end date of the project must be later than the planned start date"))

    def validate_description(form, field):
        if len(field.data.strip()) == 0:
            raise validators.ValidationError(_l("This field is mandatory!"))


class ProjectFormCreate(ProjectForm):
    def __init__(self, *args, **kwargs):
        super(ProjectFormCreate, self).__init__(*args, **kwargs)
        self.teams.choices = [(t.id, t) for t in db.session.scalars(sa.select(models.Team)).all()]
    teams = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Team.Meta.verbose_name_plural), validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l("Create"))


class ProjectFormEdit(ProjectForm):
    submit = wtforms.SubmitField(_l("Save"))


class ProjectRoleUserMeta(FormMeta):
    def __new__(cls, name, bases, attrs):
        if 'project' not in attrs:
            return super(ProjectRoleUserMeta, cls).__new__(cls, name, bases, attrs)
        all_roles = db.session.scalars(sa.select(ProjectRole).where(ProjectRole.string_slug != 'anonymous')).all()
        all_users = db.session.scalars(sa.select(User).where(User.archived == False)).all()
        attr_names = []
        for role in all_roles:
            attr_name = 'role_' + str(role.id)
            attr_value = TreeSelectMultipleField(_l("%(field_name)s:", field_name=role.title), validators=[validators.Optional()], choices=[(str(i.id), i) for i in all_users])
            attrs.update({attr_name: attr_value})
            attr_names.append(attr_name)
        instance = super(ProjectRoleUserMeta, cls).__new__(cls, name, bases, attrs)
        instance.attr_names = attr_names
        instance.project = attrs.get('project')
        return instance


class ProjectRoleUserForm(FlaskForm, metaclass=ProjectRoleUserMeta):
    def __init__(self, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        
    def load_exist_value(self):
        for participant in self.project.participants:
            current_attr = getattr(self, 'role_' + str(participant.role_id))
            if current_attr.data is None:
                current_attr.data = []
            current_attr.data.append(str(participant.user_id))
    
    def load_project_role_participants(self):
        #added new participants
        for an in self.attr_names:
            for d in getattr(self, an).data:
                p = UserRoleHasProject(project=self.project, role_id=int(an[5::]), user_id=int(d))
                self.session.add(p)


def get_project_role_user_form(project: Project) -> ProjectRoleUserForm:
    return type('ProjectRoleUserForm', (ProjectRoleUserForm,), {'project': project,
                                                                'submit': wtforms.SubmitField(_l("Save"))})


class AdditionalParametersFormMeta(FormMeta):
    def __new__(cls, name, bases, attrs):
        if 'params' not in attrs:
            return super(AdditionalParametersFormMeta, cls).__new__(cls, name, bases, attrs)
        name_list = []
        for param in attrs['params']:
            # param: ProjectAdditionalFieldData
            if not isinstance(param, models.ProjectAdditionalFieldData):
                raise ValueError('all additional parameters form must being of type ProjectAdditionalFieldData')
            new_name = 'param_' + str(param.id)
            name_list.append(new_name)
            if param.field_type.field_type == models.ProjectAdditionalParameterFieldType.StringField:
                new_item = wtforms.StringField(_l("%(field_name)s:", field_name=param.field_type.title), validators=[validators.Optional()], description=param.field_type.help_text)
            elif param.field_type.field_type == models.ProjectAdditionalParameterFieldType.TextAreaField:
                new_item = wtforms.TextAreaField(_l("%(field_name)s:", field_name=param.field_type.title), validators=[validators.Optional()], description=param.field_type.help_text)
            elif param.field_type.field_type == models.ProjectAdditionalParameterFieldType.IntegerField:
                new_item = wtforms.IntegerField(_l("%(field_name)s:", field_name=param.field_type.title), validators=[validators.Optional()], description=param.field_type.help_text)
            elif param.field_type.field_type == models.ProjectAdditionalParameterFieldType.BooleanField:
                new_item = wtforms.BooleanField(_l("%(field_name)s:", field_name=param.field_type.title), validators=[validators.Optional()], description=param.field_type.help_text)
            elif param.field_type.field_type == models.ProjectAdditionalParameterFieldType.WysiwygField:
                new_item = WysiwygField(_l("%(field_name)s:", field_name=param.field_type.title), validators=[validators.Optional()], description=param.field_type.help_text)
            else:
                raise ValueError(f'Database is corrupt: field_type of {param.field_type.field_type} does not exist')
            attrs.update({new_name: new_item})
        instance = super(AdditionalParametersFormMeta, cls).__new__(cls, name, bases, attrs)
        instance.name_list = name_list
        return instance


class AdditionalParametersForm(FlaskForm, metaclass=AdditionalParametersFormMeta):
    def populate_parameters(self, project: models.Project) -> None:
        ''' Populate additional parameters for given project '''
        for param_name in self.name_list:
            param: models.ProjectAdditionalFieldData = db.session.scalars(sa.select(models.ProjectAdditionalFieldData)
                                                                          .where(models.ProjectAdditionalFieldData.id == int(param_name[6::]))).one() # paam: models.ProjectAdditionalFieldData
            param_data = getattr(self, param_name).data
            if param.field_type.field_type == models.ProjectAdditionalParameterFieldType.BooleanField:
                param.data = str(param_data)
            elif param.field_type.field_type == models.ProjectAdditionalParameterFieldType.WysiwygField:
                param.data = sanitizer.sanitize(param_data)
            elif param.field_type.field_type == models.ProjectAdditionalParameterFieldType.IntegerField:
                param.data = str(param_data) if param_data is not None else None
            else:
                param.data = sanitizer.escape(param_data)
    def load_exist_value(self, project: models.Project):
        for param_name in self.name_list:
            param: models.ProjectAdditionalFieldData = db.session.scalars(sa.select(models.ProjectAdditionalFieldData).where(models.ProjectAdditionalFieldData.id == int(param_name[6::]))).one()
            if param.field_type.field_type == models.ProjectAdditionalParameterFieldType.BooleanField:
                getattr(self, param_name).data = param.data == 'True'
            elif param.field_type.field_type == models.ProjectAdditionalParameterFieldType.IntegerField:
                getattr(self, param_name).data = int(param.data) if param.data is not None and param.data != 'None' else None
            elif param.field_type.field_type == models.ProjectAdditionalParameterFieldType.WysiwygField:
                getattr(self, param_name).data = param.data
            else:
                getattr(self, param_name).data = sanitizer.unescape(param.data)


def get_additional_parameters_form(project: Project):
    return type('AdditionalParametersForm', (AdditionalParametersForm,), {'params': project.additional_parameters,
                                                                          'submit': wtforms.SubmitField(_l("Save"))})