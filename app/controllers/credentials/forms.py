import wtforms
import wtforms.validators as validators
from app import db
from app.controllers.forms import FlaskForm, WysiwygField, TreeSelectMultipleField, Select2Field, Select2MultipleField
import app.models as models
import sqlalchemy as sa
from flask_babel import lazy_gettext as _l
from flask import url_for, g
from app.helpers.projects_helpers import validate_service, validate_host


class CredentialForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super(CredentialForm, self).__init__(*args, **kwargs)
        self.check_wordlist_id.choices = [('0', '---')] + [(i[0], i[1]) for i in db.session.execute(sa.select(models.CheckWordlist.id, models.CheckWordlist.title))]
        self.services.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).select_from(models.Project).join(models.Project.networks).join(models.Network.to_hosts).join(models.Host.services).where(models.Project.id==project_id))]
        self.services.callback = url_for('networks.get_select2_service_data', project_id=project_id)
        self.services.locale = g.locale
        self.services.validate_funcs = lambda x: validate_service(project_id, x)
        self.received_from.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network).where(models.Network.project_id == project_id))]
        self.received_from.callback = url_for('networks.get_select2_host_data', project_id=project_id)
        self.received_from.locale = g.locale
        self.received_from.validate_funcs = lambda x: validate_host(project_id, x)

    login = wtforms.StringField(_l("%(field_name)s:", field_name=models.Credential.login.info["label"]), 
                                validators=[validators.InputRequired(message=_l("This field is mandatory!")), validators.Length(max=models.Credential.login.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Credential.login.type.length))])
    description = WysiwygField(_l("%(field_name)s:", field_name=models.Credential.description.info["label"]), validators=[validators.Optional()])
    password_hash = wtforms.StringField(_l("%(field_name)s:", field_name=models.Credential.password_hash.info["label"]), validators=[validators.Optional()])
    hash_type_id = Select2Field(models.HashType, label=_l("%(field_name)s:", field_name=models.Credential.hash_type_id.info["label"]), validators=[validators.Optional()])
    check_wordlist_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Credential.check_wordlist_id.info["label"]), validators=[validators.Optional()], description=_l("The dictionary for which the verification was performed/is planned"))
    password = wtforms.StringField(_l("%(field_name)s:", field_name=models.Credential.password.info["label"]), validators=[validators.Length(max=models.Credential.password.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Credential.password.type.length))])
    services = Select2MultipleField(models.Service, label=_l("%(field_name)s:", field_name=models.Credential.services.info["label"]), validators=[validators.Optional()], attr_title='treeselecttitle')
    is_pentest_credentials = wtforms.BooleanField(_l("%(field_name)s:", field_name=models.Credential.is_pentest_credentials.info["label"]), default=False)
    received_from = Select2MultipleField(models.Host, label=_l("%(field_name)s:", field_name=models.Credential.received_from.info["label"]), description=models.Credential.received_from.info["help_text"], validators=[validators.Optional()], attr_title="treeselecttitle")


class CredentialCreateForm(CredentialForm):
    submit = wtforms.SubmitField(_l("Create"))
    submit_and_add_new = wtforms.SubmitField(_l("Create and add another one"))


class CredentialEditForm(CredentialForm):
    submit = wtforms.SubmitField(_l("Save"))


class EditRelatedServicesForm(FlaskForm):
    def __init__(self, credential: models.Credential, *args, **kwargs):
        super(EditRelatedServicesForm, self).__init__(*args, **kwargs)
        self.services.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).join(models.Service.host).join(models.Host.from_network).where(models.Network.project_id==credential.project_id)).all()]
        self.services.data = [str(i.id) for i in credential.services]
        self.services.locale = g.locale
        self.services.callback = url_for('networks.get_select2_service_data', project_id=credential.project_id)
    services = Select2MultipleField(models.Service, label=_l("%(field_name)s:", field_name=models.Credential.services.info["label"]), validators=[validators.Optional()],
                                       id='EditRelatedServicesField', attr_title='treeselecttitle')
