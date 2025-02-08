from flask import Flask
from celery import Celery, Task
from typing import Optional, Any


class CeleryManager():
    def __init__(self, app: Optional[Flask] = None):
        if app is not None:
            # The Flask application is set explicitly:
            self.app = self.create_celery_app(app)
    
    def init_app(self, flask_app: Flask) -> None:
        self.app = self.create_celery_app(flask_app)
        flask_app.extensions["celery"] = self.app
    
    def __getattribute__(self, name: str) -> Any:
        if name in ['app', 'flask_app', 'init_app', 'create_celery_app']:
            return object.__getattribute__(self, name)
        return object.__getattribute__(self.app, name)
    
    @staticmethod
    def create_celery_app(flask_app: Flask) -> Celery:
        # If the application factory is used, we will create a new Celery type object and use it exactly
        broker_url = flask_app.config["CELERY_BROKER_URL"] if "CELERY_BROKER_URL" in flask_app.config else "redis://localhost:6379/0"
        backend_result = flask_app.config["CELERY_RESULT_BACKEND"] if 'CELERY_RESULT_BACKEND' in flask_app.config else 'redis://localhost:6379/0'
        class FlaskTask(Task):
            def __call__(self, *args: object, **kwargs: object) -> object:
                with flask_app.app_context():
                    return self.run(*args, **kwargs)
        celery_app = Celery(flask_app.name, task_cls=FlaskTask)
        celery_app.config_from_object({'broker_url': broker_url,
                                       'result_backend': backend_result, 
                                       'task_ignore_result': flask_app.config.get('CELERY_TASK_IGNORE_RESULT'),
                                       'imports': ('app', 'app.models', 'app.action_modules'),
                                       'include': ('app', 'app.action_modules'),
                                       "broker_connection_retry_on_startup": True})
        # celery_app.set_default()
        return celery_app