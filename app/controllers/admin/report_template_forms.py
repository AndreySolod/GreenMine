from app.controllers.forms import WysiwygField, FlaskForm
from app import db
from app.models import ProjectReportTemplate
import app.models as models
import wtforms
import wtforms.validators as validators
import sqlalchemy as sa
from flask_babel import lazy_gettext as _l


class ReportTemplateForm(FlaskForm):
    title = wtforms.StringField(_l("%(field_name)s:", field_name=ProjectReportTemplate.title.info["label"]), validators=[validators.InputRequired(message=_l("This field is mandatory!")),
                                                                                                                         validators.Length(min=0, max=ProjectReportTemplate.title.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(ProjectReportTemplate.title.type.length)))])
    description = wtforms.TextAreaField(_l("%(field_name)s:", field_name=ProjectReportTemplate.description.info["label"]), validators=[validators.Optional()])
    template = wtforms.FileField(_l("%(field_name)s:", field_name=ProjectReportTemplate.template.info["label"]), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])


class ReportTemplateCreateForm(ReportTemplateForm):
    submit = wtforms.SubmitField(_l("Create"))


class ReportTemplateEditForm(ReportTemplateForm):
    template = wtforms.FileField(_l("%(field_name)s:", field_name=ProjectReportTemplate.template.info["label"]), validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l("Save"))