import importlib
import logging.handlers
from flask import Flask, current_app, request, g, has_app_context, has_request_context, render_template
from config import DevelopmentConfig
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_minify import Minify
from flask_babel import Babel, lazy_gettext as _l
from sqlalchemy import MetaData
from bs4 import BeautifulSoup
from markupsafe import Markup
import sqlalchemy as sa
import sqlalchemy.orm as so
from app.extensions.celery import CeleryManager
from app.extensions.csp import CSPManager
from app.extensions.sanitizer import TextSanitizerManager
from app.extensions.moment import Moment
from app.extensions.side_libraries import SideLibraries
from app.extensions.security import PasswordPolicyManager
from flask_socketio import SocketIO
from app.action_modules import AutomationModules
from multiprocessing import Process
import atexit
import werkzeug
from pathlib import Path
from typing import Optional
import logging
logger = logging.getLogger("GreenMine")
error_logger = logging.getLogger("GreenMine internal errors")


# Convention about attribute naming for Flask-SQLAlchemy
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)

# Main parameters for Flask application:
db = SQLAlchemy(metadata=metadata)
migrate = Migrate(render_as_batch=True)
moment = Moment()
login = LoginManager()
login.login_view = 'users.user_login'
login.login_message = _l("To perform this action, you need to log in")
login.login_message_category = 'warning'
csrf = CSRFProtect() # https://docs-python.ru/packages/veb-frejmvork-flask-python/rasshirenie-flask-wtf/
minify = Minify(html=True, js=True, cssless=True)
socketio = SocketIO()
celery = CeleryManager()
automation_modules = AutomationModules()
babel = Babel()
csp = CSPManager()
sanitizer = TextSanitizerManager()
side_libraries = SideLibraries(libraries_file=Path(__file__).parent / "static_config_paths.yml", always_required_libraries=['notify', 'socketio'])
password_policy = PasswordPolicyManager(change_password_callback='users.user_change_password_callback', exempt_bp=set(['files']), exempt_endpoint=set(["generic.get_current_user_theme_style", "generic.get_ckeditor_styles"]))

class FlaskGreenMine(Flask):
    def setting_custom_attributes_for_application(self):
        # check if all default settings are corrent. Here, because we cannot do it on create_app function, else we getting error in cli
        from app.helpers.general_helpers import check_global_settings_on_init_app
        check_global_settings_on_init_app(self, logger)
    def run(self, *args, **kwargs):
        self.setting_custom_attributes_for_application()
        return super(FlaskGreenMine, self).run(*args, **kwargs)

def create_app(config_class=DevelopmentConfig, debug: bool=False) -> FlaskGreenMine:
    app = FlaskGreenMine(__name__)
    app.debug = debug
    # init all application
    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db)
    moment.init_app(app)
    login.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app)
    celery.init_app(app)
    automation_modules.init_app(app)
    csp.init_app(app)
    side_libraries.init_app(app)
    sanitizer.init_app(app)
    password_policy.init_app(app)

    # register automation module as project_object_with_permissions:
    from app.helpers.admin_helpers import project_object_with_permissions
    project_object_with_permissions(AutomationModules)

    # minify all responces for minimize traffic
    if not app.debug:
        minify.init_app(app)
    
    def get_locale():
        ''' Returned preferred locale for current user '''
        if not has_app_context() or not has_request_context():
            # in the Flask shell we have no request context
            return 'en'
        if current_user.is_authenticated:
            if not current_user.preferred_language.string_slug == 'auto':
                return current_user.preferred_language.code
        elif app.config["GlobalSettings"].default_language.string_slug != 'auto':
            return app.config["GlobalSettings"].default_language.code
        
        return request.accept_languages.best_match(app.config["LANGUAGES"])
    babel.init_app(app, locale_selector=get_locale)

    # set context processor
    from app.helpers.general_helpers import truncate_html_words, get_complementary_color, task_tree_header, random_string, is_empty_string, escapejs, as_style
    from app.helpers.main_page_helpers import DefaultEnvironment as MainPageEnvironment
    from app.controllers.generics.forms import CommentForm

    @app.context_processor
    def context_processor_flask():
        return {'truncate_html_words': truncate_html_words, 'get_complementary_color': get_complementary_color,
                'task_tree_header': task_tree_header, 'Markup': Markup, 'BeautifulSoup': BeautifulSoup,
                'comment_form': CommentForm, 'random_string': random_string, 'zip': zip,
                'getattr': getattr, 'is_empty_string': is_empty_string,
                'is_archived': False, 'models': importlib.import_module('app.models'),
                'GlobalSettings': current_app.config["GlobalSettings"], 'need_socetio': False,
                'roles': importlib.import_module('app.helpers.roles'), 'enumerate': enumerate}
    
    @app.template_filter('escapejs')
    def add_template_filter_escapejs(string: str | dict) -> Markup:
        return escapejs(string)
    
    @app.template_filter('as_style')
    def add_template_filter_as_style_attrs(attrs: dict) -> Markup:
        return as_style(attrs)
    @app.template_filter('suppress_none')
    def add_template_filter_suppressnone(string: Optional[str]) -> str:
        if string is None:
            return ""
        return string

    # blueprints
    from app.controllers import bp as extensions_bp
    from app.controllers.main_page import bp as main_page_bp
    from app.controllers.projects import bp as projects_bp
    from app.controllers.users import bp as users_bp
    from app.controllers.tasks import bp as tasks_bp
    from app.controllers.files import bp as files_bp
    from app.controllers.networks import bp as networks_bp
    from app.controllers.api import bp as api_bp
    from app.controllers.generics import bp as generic_bp
    from app.controllers.credentials import bp as credentials_bp
    from app.controllers.issues import bp as issues_bp
    from app.controllers.webfiles import bp as webfiles_bp
    from app.controllers.admin import bp as admin_bp
    from app.controllers.notes import bp as notes_bp
    from app.controllers.wiki_pages import bp as wiki_bp
    from app.controllers.cves import bp as cve_bp
    from app.controllers.action_modules import bp as action_modules_bp
    from app.controllers.chats import bp as chats_bp
    from app.controllers.reports import bp as report_template_bp
    from app.controllers.research_events import bp as research_events_bp

    app.register_blueprint(main_page_bp)
    app.register_blueprint(extensions_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(networks_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)
    app.register_blueprint(generic_bp)
    app.register_blueprint(credentials_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(webfiles_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(wiki_bp)
    app.register_blueprint(cve_bp)
    app.register_blueprint(action_modules_bp)
    app.register_blueprint(chats_bp)
    app.register_blueprint(report_template_bp)
    app.register_blueprint(research_events_bp)
    
    @app.before_request
    def set_locale():
        g.locale = str(get_locale())
    
    # Setting no autoflush to session:
    with app.app_context():
        db.session.configure(autoflush=False)
        db.technical_session = so.scoped_session(so.sessionmaker(bind=db.engine, autoflush=False, info={'is_technical': True})) # Session without autoflush, that help us to correctly create technical objects like notification etc...

    # setting logging
    if config_class.USER_ACTION_LOGGING_ON_STDOUT:
        logger.addHandler(logging.StreamHandler())
    if config_class.FLASK_LOGGING_ON_STDOUT:
        app.logger.addHandler(logging.StreamHandler())
    if config_class.USER_ACTION_LOGGING_FILE:
        file_path = Path(app.root_path).parent / config_class.USER_ACTION_LOGGING_FILE
        file_handler = logging.FileHandler(filename=file_path, mode='a+')
        file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s %(levelname)s]: %(message)s'))
        logger.addHandler(file_handler)
    if config_class.FLASK_LOGGING_FILE:
        file_path = Path(app.root_path).parent / config_class.FLASK_LOGGING_FILE
        file_handler = logging.FileHandler(filename=file_path, mode='a+')
        file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s %(levelname)s]: %(message)s'))
        app.logger.addHandler(file_handler)
    error_logger.addHandler(logging.StreamHandler())
    if config_class.ERROR_LOGGING_FILE:
        file_path = Path(app.root_path).parent / config_class.ERROR_LOGGING_FILE
        file_handler = logging.FileHandler(filename=file_path, mode='a+')
        file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s %(levelname)s]: %(message)s [in %(pathname)s:%(lineno)d]'))
        app.logger.addHandler(file_handler)
    
    # Error handlers:
    if not app.debug:
        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            db.technical_session.rollback()
            error_logger.error(error)
            ctx = MainPageEnvironment('main_page', 'show')()
            error_message = _l("Internal server error. Please report on GitVerse about this issue (log file in %(config)s)",  config=config_class.ERROR_LOGGING_FILE)
            return render_template('errors/500.html', **ctx, error_message=error_message), 500

    return app
