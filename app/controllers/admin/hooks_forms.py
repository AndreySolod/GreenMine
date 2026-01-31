from app.controllers.forms import FlaskForm, WysiwygField
from app import db
from app.models import Hook
import wtforms
import wtforms.validators as validators
import flask_wtf.file as wtfile
from flask_babel import lazy_gettext as _l
import sqlalchemy as sa
import app.models as models
import json
from flask import request


class HookForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_object.choices = [(i.name, getattr(models, i.value).Meta.verbose_name) for i in models.ObjectWithHook]
        self.on_action.choices = [(i.name, _l(i.value)) for i in models.ObjectWithHookAction]

    title = wtforms.StringField(_l("%(field_name)s:", field_name=Hook.title.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory")), validators.Length(min=0, max=Hook.title.type.length, message=_l("This field must not exceed %(length)s characters in length", length=str(Hook.title.type.length)))])
    description = WysiwygField(_l("%(field_name)s:", field_name=Hook.description.info["label"]))
    on_object = wtforms.SelectField(_l("%(field_name)s:", field_name=Hook.on_object.info["label"]), validators=[validators.DataRequired()])
    on_action = wtforms.SelectField(_l("%(field_name)s:", field_name=Hook.on_action.info["label"]), validators=[validators.DataRequired()])
    priority = wtforms.IntegerField(_l("%(field_name)s:", field_name=Hook.priority.info["label"]), description=Hook.priority.info["help_text"], validators=[validators.DataRequired(message=_l("This field is mandatory"))])
    code = wtforms.HiddenField(_l("%(field_name)s:", field_name=Hook.code.info["label"]), validators=[validators.DataRequired(message=_l("This field is mandatory"))])


class HookCreateForm(HookForm):
    submit = wtforms.SubmitField(_l("Create"))


class HookEditForm(HookForm):
    submit = wtforms.SubmitField(_l("Save"))