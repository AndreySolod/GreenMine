from app.controllers.forms import FlaskForm
import wtforms
import wtforms.validators as validators
from app.models import GlobalSettings
from flask_babel import lazy_gettext as _l
from flask import current_app


class PasswordPolicyForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    password_min_length = wtforms.IntegerField(_l("%(field_name)s:", field_name=GlobalSettings.password_min_length.info['label']), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    password_lifetime = wtforms.IntegerField(_l("%(field_name)s:", field_name=GlobalSettings.password_lifetime.info['label']), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    password_lowercase_symbol_require = wtforms.BooleanField(_l("%(field_name)s:", field_name=GlobalSettings.password_lowercase_symbol_require.info['label']))
    password_uppercase_symbol_require = wtforms.BooleanField(_l("%(field_name)s:", field_name=GlobalSettings.password_uppercase_symbol_require.info['label']))
    password_numbers_require = wtforms.BooleanField(_l("%(field_name)s:", field_name=GlobalSettings.password_numbers_require.info['label']))
    password_special_symbols_require = wtforms.BooleanField(_l("%(field_name)s:", field_name=GlobalSettings.password_special_symbols_require.info['label']))
    submit = wtforms.SubmitField(_l("Save"))