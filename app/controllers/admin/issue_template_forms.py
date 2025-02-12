from app.controllers.forms import FlaskForm, WysiwygField
from app import db
from app.models import IssueTemplate, Issue, CriticalVulnerability
import wtforms
import wtforms.validators as validators
from flask_babel import lazy_gettext as _l


def required_validators(column):
    vals = []
    if not column.nullable:
        vals.append(validators.DataRequired(message=_l("This field is mandatory!")))
    else:
        vals.append(validators.Optional())
    if column.type.__class__.__name__ == 'String' and column.type.length is not None:
        vals.append(validators.Length(max=column.type.length, message=_l('This field must not exceed %(length)s characters in length', length=str(column.type.length))))
    return vals


class IssueTemplateForm(FlaskForm):
    def __init__(self, session, *args, **kwargs):
        super(IssueTemplateForm, self).__init__(*args, **kwargs)
        self.issue_cve_id.choices = [('0', '')] + session.execute(db.select(CriticalVulnerability.id, CriticalVulnerability.title)).all()
    title = wtforms.StringField(_l("%(field_name)s:", field_name=IssueTemplate.title.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=IssueTemplate.title.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(IssueTemplate.title.type.length)))])
    string_slug = wtforms.StringField(_l("%(field_name)s:", field_name=IssueTemplate.string_slug.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=IssueTemplate.string_slug.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(IssueTemplate.string_slug.type.length)))])
    description = WysiwygField(_l("%(field_name)s:", field_name=IssueTemplate.description.info["label"]), validators=[validators.Optional()])
    issue_title = wtforms.StringField(_l("%(field_name)s:", field_name=IssueTemplate.issue_title.info["label"]), validators=required_validators(Issue.title))
    issue_description = WysiwygField(_l("%(field_name)s:", field_name=IssueTemplate.issue_description.info["label"]), validators=required_validators(Issue.description))
    issue_fix = WysiwygField(_l("%(field_name)s:", field_name=IssueTemplate.issue_fix.info["label"]), validators=required_validators(Issue.fix))
    issue_technical = WysiwygField(_l("%(field_name)s:", field_name=IssueTemplate.issue_technical.info["label"]), validators=required_validators(Issue.technical))
    issue_riscs = WysiwygField(_l("%(field_name)s:", field_name=IssueTemplate.issue_riscs.info["label"]), validators=required_validators(Issue.riscs))
    issue_references = WysiwygField(_l("%(field_name)s:", field_name=IssueTemplate.issue_references.info["label"]), validators=required_validators(Issue.references))
    issue_cvss = wtforms.FloatField(_l("%(field_name)s:", field_name=IssueTemplate.issue_cvss.info["label"]), validators=required_validators(Issue.cvss))
    issue_cve_id = wtforms.SelectField(_l("%(field_name)s:", field_name=IssueTemplate.issue_cve_id.info["label"]), validators=required_validators(Issue.cve_id))


class IssueTemplateCreateForm(IssueTemplateForm):
    submit = wtforms.SubmitField(_l("Create"))


class IssueTemplateEditForm(IssueTemplateForm):
    submit = wtforms.SubmitField(_l("Save"))