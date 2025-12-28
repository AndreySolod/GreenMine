from app.controllers.forms import FlaskForm, WysiwygField
from app import db
from app.models import IssueTemplate, Issue, CriticalVulnerability
import wtforms
import wtforms.validators as validators
import flask_wtf.file as wtfile
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa
import app.models as models
import json
from flask import request


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
    def __init__(self, template=None, *args, **kwargs):
        super(IssueTemplateForm, self).__init__(*args, **kwargs)
        self.issue_template = template
        self.issue_cve_id.choices = [('0', '')] + db.session.execute(db.select(CriticalVulnerability.id, CriticalVulnerability.title)).all()
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

    def validate_string_slug(form, field):
        another_issue_template = db.session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == field.data.strip())).first()
        if form.issue_template is not None and form.issue_template.string_slug == field.data:
            return None
        if another_issue_template is not None:
            raise validators.ValidationError(_l("Issue template with the specified string slug has already been registered"))


class IssueTemplateCreateForm(IssueTemplateForm):
    submit = wtforms.SubmitField(_l("Create"))


class IssueTemplateEditForm(IssueTemplateForm):
    submit = wtforms.SubmitField(_l("Save"))


class IssueTemplateImportForm(FlaskForm):
    import_file = wtforms.FileField(_l("Templates file:"), validators=[wtfile.FileAllowed(['json'], _l("Only JSON File allowed!"))])
    override_exist = wtforms.BooleanField(_l("Override exist issue templates:"), validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l("Import"))

    def validate_import_file(form, field):
        if field.data is None:
            raise validators.ValidationError(_l("File is required!"))
        try:
            form.import_file_data = json.loads(request.files.get(form.import_file.name).read().decode('utf8'))
        except json.JSONDecodeError:
            raise validators.ValidationError(_l("File is not a valid JSON file!"))