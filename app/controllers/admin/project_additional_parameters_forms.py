from app import db
from app.models import ProjectAdditionalField, ProjectAdditionalFieldGroup
import wtforms
import wtforms.validators as validators
from app.controllers.forms import FlaskForm, WysiwygField
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa
import app.models as models


class ProjectAdditionalParameterForm(FlaskForm):
    def __init__(self, current_parameter=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_parameter = current_parameter
        self.field_type.choices = [(str(key), str(value)) for key, value in ProjectAdditionalField.get_all_field_names().items()]
        self.group_id.choices = [(str(i), t) for i, t in db.session.execute(sa.select(ProjectAdditionalFieldGroup.id, ProjectAdditionalFieldGroup.title))]
    title = wtforms.StringField(_l("%(field_name)s:", field_name=ProjectAdditionalField.title.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=ProjectAdditionalField.title.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(ProjectAdditionalField.title.type.length)))])
    string_slug = wtforms.StringField(_l("%(field_name)s:", field_name=ProjectAdditionalField.string_slug.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=ProjectAdditionalField.string_slug.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(ProjectAdditionalField.string_slug.type.length)))])
    help_text = wtforms.StringField(_l("%(field_name)s:", field_name=ProjectAdditionalField.help_text.info["label"]), description=ProjectAdditionalField.help_text.info['help_text'], validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=ProjectAdditionalField.help_text.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(ProjectAdditionalField.help_text.type.length)))])
    description = WysiwygField(_l("%(field_name)s:", field_name=ProjectAdditionalField.description.info["label"]), validators=[validators.Optional()])
    field_type = wtforms.SelectField(_l("%(field_name)s:", field_name=ProjectAdditionalField.field_type.info["label"]), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    group_id = wtforms.SelectField(_l("%(field_name)s:", field_name=ProjectAdditionalField.group_id.info["label"]), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])

    def validate_string_slug(form, field):
        if form.current_parameter is not None and form.current_parameter.string_slug == field.data:
            return None
        elem = db.session.scalars(sa.select(models.ProjectAdditionalField).where(models.ProjectAdditionalField.string_slug == field.data)).first()
        if elem is not None:
            raise validators.ValidationError(_l("Object with specified field value already exist in database"))


class ProjectAdditionalParameterCreateForm(ProjectAdditionalParameterForm):
    submit = wtforms.SubmitField(_l("Create"))


class ProjectAdditionalParameterEditForm(ProjectAdditionalParameterForm):
    submit = wtforms.SubmitField(_l("Save"))