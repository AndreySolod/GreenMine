import app.models as models
from app import celery
from flask import Flask
from app.action_modules import AutomationModules
from app.controllers.forms import FlaskForm
from sqlalchemy.orm.session import Session
from typing import Callable, Any, Dict


class ActionModuleError(Exception):
    pass


class ActionModule:
    def __init_subclass__(cls):
        instance = cls()
        instance.exploit_task = celery.task(instance.exploit, name=instance.__class__.__name__ + "_exploit")
        AutomationModules.register_action_module(instance)
    
    title: str = "Automation module"
    description: str = "Basic class for automation module"
    admin_form: FlaskForm
    run_form: FlaskForm
    exploit_single_target: Callable
    default_options: dict = {}

    def load_default_options(self, app: Flask):
        ''' Rebuilds all forms and fills in the default_options attribute for this class '''
        # Called admin_form once to rebuild all _unbound_fields:
        with app.app_context():
            self.admin_form()
        self.default_options = {}
        for name, field in self.admin_form._unbound_fields:
            if (name == 'submit'):
                # Skipping submit button because they don't doing anything
                continue
            try:
                self.default_options[name] = field.kwargs["default"]
            except AttributeError:
                raise ActionModuleError("Default values must be specified for all fields of the admin panel form (the 'default' attribute)!")

    def run_by_single_target(self, exploit_data: dict, session: Session, running_user: models.User):
        ''' Causes the operation of this module for a given group of purposes '''
        self.exploit_single_target(session=session, running_user_id=running_user.id, **exploit_data, **self.default_options)
    
    def run(self, filled_form: FlaskForm, running_user: models.User, form_files, locale: str, project_id: int):
        ''' Causes the operation of this module for a given group of goals via a Celery task '''
        bt = self.exploit_task
        ff = {}
        for name, field in filled_form._fields.items():
            if field.__class__.__name__ == 'FileField':
                ff[name] = form_files[field.name].read()
            else:
                ff[name] = field.data
        if hasattr(filled_form, 'additional_form_attrs'):
            ff.update(filled_form.additional_form_attrs)
        bt.delay(ff, running_user.id, self.default_options, locale=locale, project_id=project_id)