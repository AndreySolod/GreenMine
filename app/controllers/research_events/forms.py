from app.controllers.forms import FlaskForm, WysiwygField, Select2Field, TreeSelectSingleField
import app.models as models
from flask import url_for, g
from app import db
import wtforms
import wtforms.validators as validators
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa
from app.helpers.projects_helpers import validate_host
from flask_login import current_user


class PentestResearchEventForm(FlaskForm):
    def __init__(self, project, *args, **kwargs):
        super(PentestResearchEventForm, self).__init__(*args, **kwargs)
        self.source_host_id.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(models.Network.project_id==project.id))]
        self.source_host_id.callback = url_for('networks.get_select2_all_host_data', project_id=project.id)
        self.source_host_id.locale = g.locale
        self.source_host_id.validate_funcs = lambda x: validate_host(project.id, x)
        self.target_host_id.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(sa.and_(models.Network.project_id==project.id, models.Host.excluded == False)))]
        self.target_host_id.callback = url_for('networks.get_select2_host_data', project_id=project.id)
        self.target_host_id.locale = g.locale
        self.target_host_id.validate_funcs = lambda x: validate_host(project.id, x)
        self.operator_id.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.User))]
        self.operator_id.callback = url_for('users.user_select2_data')
        self.operator_id.locale = g.locale
        self.operator_id.data = current_user.id
        self.mitre_attack_technique_id.choices = [('0', '')] + [ (str(i.id), i) for i in db.session.scalars(sa.select(models.MitreAttackTechnique))]
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.title.info["label"]), validators=[
                                validators.DataRequired(message=_l("This field is mandatory!")),
                                validators.Length(max=models.PentestResearchEvent.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestResearchEvent.title.type.length))])
    timestamp = wtforms.DateTimeField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.timestamp.info["label"]), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    source_host_id = Select2Field(models.Host, label=_l("%(field_name)s:", field_name=models.PentestResearchEvent.source_host_id.info["label"]),
                                  description=models.PentestResearchEvent.source_host_id.info["help_text"],
                                  validators=[validators.Optional()],
                                  attr_title="treeselecttitle")
    source_user = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.source_user.info["label"]), validators=[
                                validators.Length(min=0, max=models.PentestResearchEvent.source_user.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestResearchEvent.source_user.type.length))])
    source_process = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.source_process.info["label"]), validators=[
                                validators.Length(min=0, max=models.PentestResearchEvent.source_process.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestResearchEvent.source_process.type.length))])
    target_host_id = Select2Field(models.Host, label=_l("%(field_name)s:", field_name=models.PentestResearchEvent.target_host_id.info["label"]),
                                  description=models.PentestResearchEvent.target_host_id.info["help_text"],
                                  validators=[validators.Optional()],
                                  attr_title="treeselecttitle")
    target_user = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.target_user.info["label"]), validators=[
                                validators.Length(min=0, max=models.PentestResearchEvent.target_user.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestResearchEvent.target_user.type.length))])
    target_process = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.target_process.info["label"]), validators=[
                                validators.Length(min=0, max=models.PentestResearchEvent.target_process.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestResearchEvent.target_process.type.length))])
    operator_id = Select2Field(models.User, label=_l("%(field_name)s:", field_name=models.PentestResearchEvent.operator_id.info["label"]),
                                  description=models.PentestResearchEvent.operator_id.info["help_text"],
                                  validators=[validators.InputRequired(message=_l("This field is mandatory!"))],
                                  attr_title="treeselecttitle")
    description = WysiwygField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.description.info["label"]), validators=[validators.Optional()])
    raw_evidence = WysiwygField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.raw_evidence.info["label"]), validators=[validators.Optional()])
    detected_id = Select2Field(models.EvidenceOfEventDetected, label=_l("%(field_name)s:", field_name=models.PentestResearchEvent.detected.info["label"]), validators=[validators.InputRequired()])
    prevented_id = Select2Field(models.EvidenceOfEventPrevented, label=_l("%(field_name)s:", field_name=models.PentestResearchEvent.prevented.info["label"]), validators=[validators.InputRequired()])
    mitre_attack_technique_id = TreeSelectSingleField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.mitre_attack_technique_id.info["label"]), validators=[validators.Optional()])


class PentestResearchEventCreateForm(PentestResearchEventForm):
    submit = wtforms.SubmitField(_l("Create"))


class PentestResearchEventEditForm(PentestResearchEventForm):
    submit = wtforms.SubmitField(_l("Save"))


class PentestOrganizationDetectionEventForm(FlaskForm):
    def __init__(self, project, *args, **kwargs):
        super(PentestOrganizationDetectionEventForm, self).__init__(*args, **kwargs)
        self.source_host_id.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(models.Network.project_id==project.id))]
        self.source_host_id.callback = url_for('networks.get_select2_all_host_data', project_id=project.id)
        self.source_host_id.locale = g.locale
        self.source_host_id.validate_funcs = lambda x: validate_host(project.id, x)
        self.target_host_id.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network, isouter=True).where(sa.and_(models.Network.project_id==project.id, models.Host.excluded == False)))]
        self.target_host_id.callback = url_for('networks.get_select2_host_data', project_id=project.id)
        self.target_host_id.locale = g.locale
        self.target_host_id.validate_funcs = lambda x: validate_host(project.id, x)
        self.mitre_attack_technique_id.choices = [('0', '')] + [(str(i.id), i) for i in db.session.scalars(sa.select(models.MitreAttackTechnique))]
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestOrganizationDetectionEvent.title.info["label"]), validators=[
                                validators.DataRequired(message=_l("This field is mandatory!")),
                                validators.Length(max=models.PentestOrganizationDetectionEvent.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestOrganizationDetectionEvent.title.type.length))])
    timestamp = wtforms.DateTimeField(_l("%(field_name)s:", field_name=models.PentestOrganizationDetectionEvent.timestamp.info["label"]), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    source_host_id = Select2Field(models.Host, label=_l("%(field_name)s:", field_name=models.PentestOrganizationDetectionEvent.source_host_id.info["label"]),
                                  validators=[validators.Optional()],
                                  attr_title="treeselecttitle")
    source_user = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestOrganizationDetectionEvent.source_user.info["label"]), validators=[
                                validators.Length(min=0, max=models.PentestOrganizationDetectionEvent.source_user.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestOrganizationDetectionEvent.source_user.type.length))])
    source_process = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestOrganizationDetectionEvent.source_process.info["label"]), validators=[
                                validators.Length(min=0, max=models.PentestOrganizationDetectionEvent.source_process.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestOrganizationDetectionEvent.source_process.type.length))])
    target_host_id = Select2Field(models.Host, label=_l("%(field_name)s:", field_name=models.PentestOrganizationDetectionEvent.target_host_id.info["label"]),
                                  validators=[validators.Optional()],
                                  attr_title="treeselecttitle")
    target_user = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestOrganizationDetectionEvent.target_user.info["label"]), validators=[
                                validators.Length(min=0, max=models.PentestOrganizationDetectionEvent.target_user.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestOrganizationDetectionEvent.target_user.type.length))])
    target_process = wtforms.StringField(_l("%(field_name)s:", field_name=models.PentestOrganizationDetectionEvent.target_process.info["label"]), validators=[
                                validators.Length(min=0, max=models.PentestOrganizationDetectionEvent.target_process.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.PentestOrganizationDetectionEvent.target_process.type.length))])
    description = WysiwygField(_l("%(field_name)s:", field_name=models.PentestOrganizationDetectionEvent.description.info["label"]), validators=[validators.Optional()])
    mitre_attack_technique_id = TreeSelectSingleField(_l("%(field_name)s:", field_name=models.PentestResearchEvent.mitre_attack_technique_id.info["label"]), validators=[validators.Optional()])


class PentestOrganizationDetectionEventCreateForm(PentestOrganizationDetectionEventForm):
    submit = wtforms.SubmitField(_l("Create"))


class PentestOrganizationDetectionEventEditForm(PentestOrganizationDetectionEventForm):
    submit = wtforms.SubmitField(_l("Save"))