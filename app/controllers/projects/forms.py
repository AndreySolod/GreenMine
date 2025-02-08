from app import db
from app.controllers.forms import FlaskForm, WysiwygField, TreeSelectMultipleField
import wtforms
import wtforms.validators as validators
from wtforms.form import FormMeta
from app.helpers.general_helpers import utcnow
from app.models import User, Project, ProjectRole, UserRoleHasProject
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa


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
    submit = wtforms.SubmitField(_l("Create"))

    def validate_end_at(form, field):
        if field.data < form.start_at.data:
            raise validators.ValidationError(_l("The planned end date of the project must be later than the planned start date"))

    def validate_description(form, field):
        if len(field.data.strip()) == 0:
            raise validators.ValidationError(_l("This field is mandatory!"))


class EditProjectForm(ProjectForm):
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