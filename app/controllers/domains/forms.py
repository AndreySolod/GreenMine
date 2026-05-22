import wtforms
import wtforms.validators as validators
from app import db
from app.controllers.forms import WysiwygField, FlaskForm, Select2MultipleField
from app.helpers.projects_helpers import validate_host, validate_credential
import app.models as models
from flask_babel import lazy_gettext as _l
from flask import g, url_for
import sqlalchemy as sa


class DomainForm(FlaskForm):
    def __init__(self, project: models.Project, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.domain_controllers.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(models.Network.project_id == project.id))]
        self.domain_controllers.locale = g.locale
        self.domain_controllers.callback = url_for('networks.get_select2_host_data', project_id=project.id)
        self.domain_controllers.validate_funcs = lambda x: validate_host(project.id, x)
        self.hosts.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(models.Network.project_id == project.id))]
        self.hosts.locale = g.locale
        self.hosts.callback = url_for('networks.get_select2_host_data', project_id=project.id)
        self.hosts.validate_funcs = lambda x: validate_host(project.id, x)
        self.credentials.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Credential).where(models.Credential.project_id == project.id))]
        self.credentials.locale = g.locale
        self.credentials.callback = url_for('credentials.get_select2_credentials_data', project_id=project.id)
        self.credentials.validate_funcs = lambda x: validate_credential(project.id, x)

    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.Network.title.info["label"]),
                                validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=models.Network.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Network.title.type.length))])
    description = WysiwygField(_l("%(field_name)s:", field_name=models.Network.description.info["label"]), validators=[validators.Optional()])
    domain_controllers = Select2MultipleField(models.Host, _l("%(field_name)s:", field_name=models.Domain.domain_controllers.info["label"]), validators=[validators.Optional()],attr_title="treeselecttitle")
    hosts = Select2MultipleField(models.Host, _l("%(field_name)s:", field_name=models.Domain.hosts.info["label"]), validators=[validators.Optional()], attr_title="treeselecttitle")
    credentials = Select2MultipleField(models.Credential, _l("%(field_name)s:", field_name=models.Domain.credentials.info["label"]), validators=[validators.Optional()], attr_title="treeselecttitle")


class DomainCreateForm(DomainForm):
    submit = wtforms.SubmitField(_l("Create"))
    submit_and_add_new = wtforms.SubmitField(_l("Create and add another one"))


class DomainEditForm(DomainForm):
    submit = wtforms.SubmitField(_l("Edit"))