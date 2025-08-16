from app.controllers.forms import FlaskForm
import wtforms
import wtforms.validators as validators
from app.models import GlobalSettings
from flask_babel import lazy_gettext as _l
from flask import current_app


class AuthenticationParametersForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    authentication_method = wtforms.SelectField(_l("%(field_name)s:", field_name=GlobalSettings.authentication_method.info['label']), choices=[('password', _l('Password')), ('request_header', _l('Request Header'))])
    authentication_request_header_name = wtforms.StringField(_l("%(field_name)s:",
                                                                field_name=GlobalSettings.authentication_request_header_name.info['label']),
                                                                validators=[validators.Optional(),
                                                                            validators.Length(min=0, max=GlobalSettings.authentication_request_header_name.type.length,
                                                                                              message=_l("This field must not exceed %(length)s characters in length", length=GlobalSettings.authentication_request_header_name.type.length))])
    authentication_request_header_allow_registration = wtforms.BooleanField(_l("%(field_name)s:", field_name=GlobalSettings.authentication_request_header_allow_registration.info['label']), validators=[validators.Optional()])
    password_min_length = wtforms.IntegerField(_l("%(field_name)s:", field_name=GlobalSettings.password_min_length.info['label']), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    password_lifetime = wtforms.IntegerField(_l("%(field_name)s:", field_name=GlobalSettings.password_lifetime.info['label']), validators=[validators.InputRequired(message=_l("This field is mandatory!"))])
    password_lowercase_symbol_require = wtforms.BooleanField(_l("%(field_name)s:", field_name=GlobalSettings.password_lowercase_symbol_require.info['label']))
    password_uppercase_symbol_require = wtforms.BooleanField(_l("%(field_name)s:", field_name=GlobalSettings.password_uppercase_symbol_require.info['label']))
    password_numbers_require = wtforms.BooleanField(_l("%(field_name)s:", field_name=GlobalSettings.password_numbers_require.info['label']))
    password_special_symbols_require = wtforms.BooleanField(_l("%(field_name)s:", field_name=GlobalSettings.password_special_symbols_require.info['label']))
    submit = wtforms.SubmitField(_l("Save"))