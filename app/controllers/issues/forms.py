import wtforms
import wtforms.validators as validators
from app import db
from app.controllers.forms import FlaskForm, WysiwygField, TreeSelectMultipleField, Select2MultipleField
import app.models as models
from flask_babel import lazy_gettext as _l
from flask import url_for, g
import sqlalchemy as sa
from app.helpers.projects_helpers import validate_service


class IssueForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super(IssueForm, self).__init__(*args, **kwargs)
        self.cve_id.choices = [('0', '---')] + [(i[0], i[1]) for i in db.session.execute(sa.select(models.CriticalVulnerability.id, models.CriticalVulnerability.title))]
        self.status_id.choices = [(i[0], i[1]) for i in db.session.execute(sa.select(models.IssueStatus.id, models.IssueStatus.title))]
        self.tasks_by_issue.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.project_id==project_id))]
        self.services.callback = url_for('networks.get_select2_service_data', project_id=project_id)
        self.services.locale = g.locale
        self.services.validate_funcs = lambda x: validate_service(project_id, x)
    title = wtforms.StringField(_l("%(field_name)s:", field_name=models.Issue.title.info["label"]),
                                validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=models.Issue.title.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.Issue.title.type.length))])
    description = WysiwygField(_l("%(field_name)s:", field_name=models.Issue.description.info["label"]), validators=[validators.Optional()])
    by_template_slug = wtforms.StringField(_l("%(field_name)s:", field_name=models.Issue.by_template_slug.info["label"]), validators=[validators.Optional()])
    fix = WysiwygField(_l("%(field_name)s:", field_name=models.Issue.fix.info["label"]),
                       validators=[validators.Optional()], description=_l("What is required to fix this problem"))
    technical = WysiwygField(_l("%(field_name)s:", field_name=models.Issue.technical.info["label"]),
                             validators=[validators.Optional()], description=_l("Additional technical information about the problem"))
    riscs = WysiwygField(_l("%(field_name)s:", field_name=models.Issue.riscs.info["label"]),
                         validators=[validators.Optional()], description=_l("The risks of exploiting this problem"))
    references = WysiwygField(_l("%(field_name)s:", field_name=models.Issue.references.info["label"]),
                              validators=[validators.Optional()], description=_l("Additional links with information about the problem"))
    cvss = wtforms.FloatField(_l("%(field_name)s:", field_name=models.Issue.cvss.info["label"]), validators=[validators.Optional()])
    cve_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Issue.cve_id.info["label"]), validators=[validators.Optional()])
    status_id = wtforms.SelectField(_l("%(field_name)s:", field_name=models.Issue.status_id.info["label"]), validators=[validators.Optional()])
    services = Select2MultipleField(models.Service, label=_l("%(field_name)s:", field_name=models.Issue.services.info["label"]), validators=[validators.Optional()], attr_title='treeselecttitle')
    tasks_by_issue = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Issue.tasks_by_issue.info["label"]), validators=[validators.Optional()])


class IssueCreateForm(IssueForm):
    submit = wtforms.SubmitField(_l('Create'))
    submit_and_add_new = wtforms.SubmitField(_l("Create and add another one"))


class IssueEditForm(IssueForm):
    submit = wtforms.SubmitField(_l("Save"))


class EditRelatedObjectsForm(FlaskForm):
    def __init__(self, issue: models.Issue, *args, **kwargs):
        super(EditRelatedObjectsForm, self).__init__(*args, **kwargs)
        self.services.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).join(models.Service.host).join(models.Host.from_network).where(models.Network.project_id==issue.project_id)).all()]
        self.tasks_by_issue.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.ProjectTask).where(models.ProjectTask.project_id==issue.project_id)).all()]
        self.services.data = [str(i.id) for i in issue.services]
        self.services.locale = g.locale
        self.services.callback = url_for('networks.get_select2_service_data', project_id=issue.project_id)
        self.tasks_by_issue.data = [str(i.id) for i in issue.tasks_by_issue]
    services = Select2MultipleField(models.Service, _l("%(field_name)s:", field_name=models.Issue.services.info["label"]), validators=[validators.Optional()],
                                    id='EditRelatedServicesField', attr_title='treeselecttitle')
    tasks_by_issue = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.Issue.tasks_by_issue.info["label"]), validators=[validators.Optional()], id='EditRelatedTasksField')
