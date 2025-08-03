from app import db
from app.controllers.forms import FlaskForm, WysiwygField, TreeSelectMultipleField
import wtforms
from wtforms.form import FormMeta
import wtforms.validators as validators
import app.models as models
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa
from flask_login import current_user


class TeamMemberMeta(FormMeta):
    def __new__(cls, name, bases, attrs):
        if 'team' not in attrs:
            return super(TeamMemberMeta, cls).__new__(cls, name, bases, attrs)
        all_roles = db.session.scalars(sa.select(models.ProjectRole).where(models.ProjectRole.string_slug != 'anonymous')).all()
        all_users = db.session.scalars(sa.select(models.User).where(models.User.archived == False)).all()
        attr_names = []
        for role in all_roles:
            attr_name = 'role_' + str(role.id)
            attr_value = TreeSelectMultipleField(_l("%(field_name)s:", field_name=role.title), validators=[validators.Optional()], choices=[(str(i.id), i) for i in all_users])
            attrs.update({attr_name: attr_value})
            attr_names.append(attr_name)
        instance = super(TeamMemberMeta, cls).__new__(cls, name, bases, attrs)
        instance.attr_names = attr_names
        instance.team = attrs.get('team')
        return instance


class TeamMemberForm(FlaskForm, metaclass=TeamMemberMeta):
        
    def load_exist_members(self):
        for member in self.team.members:
            current_attr = getattr(self, 'role_' + str(member.role_id))
            if current_attr.data is None:
                current_attr.data = []
            current_attr.data.append(str(member.user_id))
    
    def load_team_members(self):
        #added new members
        for member in self.team.members:
            db.session.delete(member)
        for an in self.attr_names:
            for d in getattr(self, an).data:
                p = models.UserHasTeam(role_id=int(an[5::]), user_id=int(d), team=self.team)
                db.session.add(p)


def get_team_members_form(team: models.Team) -> TeamMemberForm:
    return type('TeamMemberForm', (TeamMemberForm,), {'team': team,
                                                      'submit': wtforms.SubmitField(_l("Save"))})


class TeamsForm(TeamMemberForm):
    def __init__(self, *args, **kwargs):
        super(TeamMemberForm, self).__init__(*args, **kwargs)
        self.leader_id.choices = [(str(i), j) for i, j in db.session.execute(sa.select(models.User.id, models.User.title)).all()]
        self.leader_id.data = str(current_user.id)
    title = wtforms.StringField(_l("%(field_name)s", field_name=models.Team.title.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                                                                                              validators.Length(max=models.Team.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Team.title.type.length))])
    description = wtforms.TextAreaField(_l("%(field_name)s", field_name=models.Team.description.info["label"]), validators=[validators.Optional()])
    leader_id = wtforms.SelectField(_l("%(field_name)s", field_name=models.Team.leader_id.info["label"]))

    def populate_obj(self, session, o, current_user=None):
        super().populate_obj(session, o, current_user)
        self.team = o


class TeamCreateForm(TeamsForm):
    submit = wtforms.SubmitField(_l("Create"))


def get_team_create_form() -> TeamCreateForm:
    return type('TeamCreateForm', (TeamCreateForm,), {'team': None})

class TeamEditForm(TeamsForm):
    submit = wtforms.SubmitField(_l("Save"))

def get_team_edit_form(team: models.Team) -> TeamEditForm:
    return type('TeamEditForm', (TeamEditForm,), {'team': team})