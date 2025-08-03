from app.controllers.forms import FlaskForm, Select2Field, WysiwygField
from app import db
from app.models import CredentialImportTemplate
import sqlalchemy as sa
import app.models as models
from flask_babel import lazy_gettext as _l
import wtforms
from wtforms import validators


class CredentialImportTemplateForm(FlaskForm):
    def __init__(self, credential_template=None, *args, **kwargs):
        super(CredentialImportTemplateForm, self).__init__(*args, **kwargs)
        self.credential_template = credential_template
        self.static_check_wordlist_id.choices = [('0', '---')] + [(i[0], i[1]) for i in db.session.execute(sa.select(models.CheckWordlist.id, models.CheckWordlist.title))]
    title = wtforms.StringField(_l("%(field_name)s:", field_name=CredentialImportTemplate.title.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=CredentialImportTemplate.title.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(CredentialImportTemplate.title.type.length)))])
    string_slug = wtforms.StringField(_l("%(field_name)s:", field_name=CredentialImportTemplate.string_slug.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.Length(max=CredentialImportTemplate.string_slug.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(CredentialImportTemplate.string_slug.type.length)))])
    description = WysiwygField(_l("%(field_name)s:", field_name=CredentialImportTemplate.description.info["label"]), validators=[validators.Optional()])
    login_column_number = wtforms.IntegerField(_l("%(field_name)s:", field_name=CredentialImportTemplate.login_column_number.info["label"]), validators=[validators.Optional()])
    password_hash_column_number = wtforms.IntegerField(_l("%(field_name)s:", field_name=CredentialImportTemplate.password_hash_column_number.info["label"]), validators=[validators.Optional()])
    description_column_number = wtforms.IntegerField(_l("%(field_name)s:", field_name=CredentialImportTemplate.description_column_number.info["label"]), validators=[validators.Optional()])
    password_column_number = wtforms.IntegerField(_l("%(field_name)s:", field_name=CredentialImportTemplate.password_column_number.info["label"]), validators=[validators.Optional()])
    static_login = wtforms.StringField(_l("%(field_name)s:", field_name=CredentialImportTemplate.static_login.info["label"]), validators=[validators.Length(min=0, max=CredentialImportTemplate.static_login.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(CredentialImportTemplate.static_login.type.length)))])
    static_password_hash = wtforms.StringField(_l("%(field_name)s:", field_name=CredentialImportTemplate.static_password_hash.info["label"]), validators=[validators.Optional()])
    static_hash_type_id = Select2Field(models.HashType, label=_l("%(field_name)s:", field_name=CredentialImportTemplate.static_hash_type_id.info["label"]), validators=[validators.Optional()])
    static_check_wordlist_id = wtforms.SelectField(_l("%(field_name)s:", field_name=CredentialImportTemplate.static_check_wordlist_id.info["label"]), validators=[validators.Optional()])
    static_description = wtforms.StringField(_l("%(field_name)s:", field_name=CredentialImportTemplate.static_description.info["label"]), validators=[validators.Optional()])

    def validate_string_slug(form, field):
        if form.credential_template is not None and form.credential_template.string_slug == field.data:
            return None
        another_credential_template = db.session.scalars(sa.select(CredentialImportTemplate).where(CredentialImportTemplate.string_slug == field.data.strip())).first()
        if another_credential_template is not None:
            raise validators.ValidationError(_l("Credential import template with the specified string slug has already been registered"))


class CredentialImportTemplateFormCreate(CredentialImportTemplateForm):
    submit = wtforms.SubmitField(_l("Create"))


class CredentialImportTemplateFormEdit(CredentialImportTemplateForm):
    submit = wtforms.SubmitField(_l("Save"))