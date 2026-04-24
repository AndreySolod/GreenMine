import app.models as models
from app import celery, db, celery_task_observer
from flask import Flask
from app.action_modules import AutomationModules
from app.controllers.forms import FlaskForm
from sqlalchemy.orm.session import Session
from typing import Callable, Any, Dict
from flask_babel import lazy_gettext as _l, force_locale, gettext
import time
import logging
logger = logging.getLogger("ActionModule")


class ActionModuleError(Exception):
    pass


class ActionModule:
    def __init_subclass__(cls):
        instance = cls()
        instance.exploit_task = celery.task(instance.exploit, name=instance.__class__.__name__ + "_exploit")
        AutomationModules.register_action_module(instance)
    
    title: str = "Automation module"
    description: str = "Basic class for automation module"
    link_to_object: str = "#"
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
        async_result = bt.delay(ff, running_user.id, self.default_options, locale=locale, project_id=project_id)
        celery_task_observer.add_task(self._monitor_celery_task, async_result.id, task_name=self.title, running_user_id=running_user.id)


    def _monitor_celery_task(self, async_result_id: str, task_name: str, running_user_id: int):
        """Observer-function, performed in TaskProcessor"""
        _l('The celery task "%(task_name)s" was completed successfully.')
        async_result = celery.AsyncResult(async_result_id)
        logger.info(f"Monitoring Celery task {task_name} (id={async_result.id})")
        
        # Отладка: убедимся, что задача видна и бекенд работает
        print(f"Initial state: {async_result.state}, backend: {async_result.backend}")
        try:
            while not async_result.ready():
                time.sleep(1)
                # Опционально: прерывание по флагу остановки TaskProcessor
                #if threading.current_thread().is_shutdown(): break
            
            if async_result.successful():
                result = async_result.get()
                logger.info(f"Celery task {task_name} completed successfully. Result: {result}")
                u: models.User = db.celery_monitor_session.get(models.User, running_user_id)
                with force_locale(u.last_used_language_code):
                    task_name = gettext(task_name)
                un = models.UserNotification(to_user=u, by_user=u, description='The celery task "%(task_name)s" was completed successfully.',
                                             technical_info={'task_name': str(task_name)}, notification_type=models.UserNotificationType.SUCCESS, link_to_object=self.link_to_object)
                db.celery_monitor_session.add(un)
                db.celery_monitor_session.commit()
            else:
                try:
                    exc = async_result.get(propagate=False)
                    logger.error(f"Celery task {task_name} failed. Exception: {exc}")
                except Exception as e:
                    logger.error(f"Celery task {task_name} failed with unknown error: {e}")
        except Exception as e:
            logger.error(f"Error while monitoring Celery task {task_name}: {e}")
