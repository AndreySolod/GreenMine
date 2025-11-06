from app.controllers.forms import WysiwygField, FlaskForm
from app import db
from app.models import ProjectTaskTemplate
import app.models as models
import wtforms
import wtforms.validators as validators
import flask_wtf.file as wtfile
import sqlalchemy as sa
from flask_babel import lazy_gettext as _l


class TaskTemplateForm(FlaskForm):
    def __init__(self, template=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_template = template
        self.task_tracker_id.choices = [('0', '---')] + db.session.execute(sa.select(models.ProjectTaskTracker.id, models.ProjectTaskTracker.title)).all()
        self.task_priority_id.choices = [('0', '---')] + db.session.execute(sa.select(models.ProjectTaskPriority.id, models.ProjectTaskPriority.title)).all()
    title = wtforms.StringField(_l("%(field_name)s:", field_name=ProjectTaskTemplate.title.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=ProjectTaskTemplate.title.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(ProjectTaskTemplate.title.type.length)))])
    string_slug = wtforms.StringField(_l("%(field_name)s:", field_name=ProjectTaskTemplate.string_slug.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=ProjectTaskTemplate.string_slug.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(ProjectTaskTemplate.string_slug.type.length)))])
    description = WysiwygField(_l("%(field_name)s:", field_name=ProjectTaskTemplate.description.info["label"]), validators=[validators.Optional()])
    task_title = wtforms.StringField(_l("%(field_name)s:", field_name=ProjectTaskTemplate.task_title.info["label"]), validators=[validators.Length(min=0, max=ProjectTaskTemplate.task_title.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(ProjectTaskTemplate.task_title.type.length)))])
    task_description = WysiwygField(_l("%(field_name)s:", field_name=ProjectTaskTemplate.task_description.info["label"]), validators=[validators.Optional()])
    task_tracker_id = wtforms.SelectField(_l("%(field_name)s:", field_name=ProjectTaskTemplate.task_tracker_id.info["label"]), validators=[validators.Optional()])
    task_priority_id = wtforms.SelectField(_l("%(field_name)s:", field_name=ProjectTaskTemplate.task_priority_id.info["label"]), validators=[validators.Optional()])
    task_estimation_time_cost = wtforms.IntegerField(_l("%(field_name)s:", field_name=ProjectTaskTemplate.task_estimation_time_cost.info["label"]), validators=[validators.Optional()])

    def validate_string_slug(form, field):
        if form.task_template is not None and form.task_template.string_slug == field.data:
            return None
        elem = db.session.scalars(sa.select(models.ProjectTaskTemplate).where(models.ProjectTaskTemplate.string_slug == field.data)).first()
        if elem is not None:
            raise validators.ValidationError(_l("Object with specified field value already exist in database"))


class TaskTemplateCreateForm(TaskTemplateForm):
    submit = wtforms.SubmitField(_l("Create"))


class TaskTemplateEditForm(TaskTemplateForm):
    submit = wtforms.SubmitField(_l("Save"))


class TaskTemplateImportForm(FlaskForm):
    import_file = wtforms.FileField(_l("Templates file:"), validators=[wtfile.FileAllowed(['json'], _l("Only JSON File allowed!"))])
    override_exist = wtforms.BooleanField(_l("Override exist task templates:"), validators=[validators.Optional()])
    submit = wtforms.SubmitField(_l("Import"))