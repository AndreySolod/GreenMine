from app.controllers.forms import FlaskForm, TreeSelectMultipleField
from app.extensions.security import check_password_complexity, check_password_hash
from flask_login import current_user
import app.models as models
import flask_wtf.file as wtfile
import wtforms
import wtforms.validators as validators
from app import db
from flask_babel import lazy_gettext as _l
from flask import current_app


class LoginForm(FlaskForm):
    login = wtforms.StringField(_l("%(field_name)s", field_name=models.User.login.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory!"))])
    password = wtforms.PasswordField(_l("Password"), validators=[validators.DataRequired(message=_l("This field is mandatory!"))])
    remember_me = wtforms.BooleanField(_l("Remember me"), default=True)
    submit = wtforms.SubmitField(_l("Enter"))


class EditUserPasswordForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.password.validators.append(validators.Length(min=current_app.config["GlobalSettings"].password_min_length))
    password = wtforms.PasswordField(_l("Password:"), validators=[validators.DataRequired(message=_l("This field is mandatory!"))])
    password_again = wtforms.PasswordField(_l("Password again:"), validators=[validators.DataRequired(message=_l("This field is mandatory!")), validators.EqualTo("password", message=_l("Must match the password field"))])
    change_on_next_request = wtforms.BooleanField(_l("Change password on the next time log in:"), default=False)
    submit = wtforms.SubmitField(_l("Confirm"))

    def validate_password(form, field):
        errors = check_password_complexity(field.data)
        if check_password_hash(current_user.password_hash, field.data):
            errors.append(_l("The new password must be different from the old one"))
        if len(errors) != 0:
            raise validators.ValidationError("; ".join(list(map(str, errors))))


class UserForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.position.choices = [(p[0], p[1]) for p in db.session.execute(db.select(models.UserPosition.id, models.UserPosition.title)).all()]
        self.manager.choices = [(p.id, p.title) for p in db.session.scalars(db.select(models.User)).all()]
        self.programming_language_theme.choices = [(p[0], p[1]) for p in db.session.execute(db.select(models.ProgrammingLanguageTheme.id, models.ProgrammingLanguageTheme.title))]
        self.theme_style.choices = [(p[0], p[1]) for p in db.session.execute(db.select(models.UserThemeStyle.id, models.UserThemeStyle.title))]
        self.programming_languages.choices = [(str(p.id), p) for p in db.session.scalars(db.select(models.ProgrammingLanguage))]
    first_name = wtforms.StringField(_l("%(field_name)s:", field_name=models.User.first_name.info["label"]),
                                     validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                                 validators.Length(max=models.User.first_name.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.User.first_name.type.length))])
    last_name = wtforms.StringField(_l("%(field_name)s:", field_name=models.User.last_name.info["label"]),
                                    validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                                validators.Length(max=models.User.last_name.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.User.last_name.type.length))])
    middle_name = wtforms.StringField(_l("%(field_name)s:", field_name=models.User.middle_name.info["label"]),
                                      validators=[validators.Length(max=models.User.middle_name.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.User.middle_name.type.length))])
    email = wtforms.EmailField(_l("%(field_name)s:", field_name=models.User.email.info["label"]),
                               validators=[validators.Optional(), validators.Email(message=_l("Enter correct E-mail"))])
    avatar = wtforms.FileField(_l("%(field_name)s:", field_name=models.User.avatar.info["label"]),
                               validators=[wtfile.FileAllowed(['jpg', 'jpeg', 'png'], _l("Only images!"))])
    position = wtforms.SelectField(_l("%(field_name)s:", field_name=models.User.position.info["label"]),
                                   validators=[validators.DataRequired(message=_l("This field is mandatory!"))])
    manager = wtforms.SelectField(_l("%(field_name)s:", field_name=models.User.manager.info["label"]),
                                  validators=[validators.DataRequired(message=_l("This field is mandatory!"))])
    programming_language_theme = wtforms.SelectField(_l("%(field_name)s:", field_name=models.User.programming_language_theme.info["label"]),
                                                     validators=[validators.DataRequired(message=_l("This field is mandatory!"))])
    theme_style = wtforms.SelectField(_l("%(field_name)s:", field_name=models.User.theme_style.info["label"]),
                                      validators=[validators.DataRequired(message=_l("This field is mandatory!"))])
    programming_languages = TreeSelectMultipleField(_l("%(field_name)s:", field_name=models.User.programming_languages.info["label"]),
                                                    validators=[validators.DataRequired(message=_l("This field is mandatory!"))])


class UserFormCreate(UserForm):
    login = wtforms.StringField(_l("%(field_name)s:", field_name=models.User.login.info["label"]),
                                validators=[validators.DataRequired(message=_l("This field is mandatory!")),
                                            validators.Length(max=models.User.login.type.length, message=_l('This field must not exceed %(length)s characters in length', length=models.User.login.type.length)),
                                            validators.Regexp('^[a-zA-Z]+[a-zA-Z0-9\\-_]*$', message=_l("Use only valid symbol (A-Z, a-z, 0-9)!"))])
    password = wtforms.PasswordField(_l("Password:"), validators=[validators.DataRequired(message=_l("This field is mandatory!"))])
    password_again = wtforms.PasswordField(_l("Password again"), validators=[validators.EqualTo("password", message=_l("Must match the password field"))])
    submit = wtforms.SubmitField(_l("Create"))

    def validate_login(form, field):
        u = db.session.scalars(db.select(models.User).where(models.User.login==field.data)).first()
        if u is not None:
            raise validators.ValidationError(_l("A user with this username already exists!"))


class UserFormEdit(UserForm):
    submit = wtforms.SubmitField(_l("Save"))


class UserFormDelete(FlaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    user_id = wtforms.StringField(_l("%(field_name)s:", field_name=models.User.id.info["label"]), validators=[validators.DataRequired()])

    def validate_user_id(form, field):
        try:
            field.data = int(field.data)
        except (ValueError, TypeError):
            raise validators.ValidationError("data must being an integer field")