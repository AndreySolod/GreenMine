import os
import secrets
from py_vapid import Vapid
from pathlib import Path
import sys
import logging
logger = logging.getLogger("Configuration")


basedir = Path(os.path.dirname(__file__))


class DevelopmentConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'very long secret'
    if os.environ.get('SESSION_COOKIE_SECURE') == None:
        SESSION_COOKIE_SECURE = False
    else:
        SESSION_COOKIE_SECURE = bool(os.environ.get('SESSION_COOKIE_SECURE'))
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE') or 'Lax'
    try:
        WTF_CSRF_TIME_LIMIT = int(os.environ.get('WTF_CSRF_TIME_LIMIT')) or 3600
    except (ValueError, TypeError):
        WTF_CSRF_TIME_LIMIT = 3600
    APPLICATION_ROOT = os.environ.get("APPLICATION_ROOT") or "/"
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + str((basedir / 'app.db').absolute())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REST_FORBIDDEN_ATTRIBUTES = os.environ.get("REST_FORBIDDEN_ATTRIBUTES").split(",") if os.environ.get("REST_FORBIDDEN_ATTRIBUTES") else ["User.password_hash", "User.token", "User.token_expiration"]
    TOKEN_EXPIRATION = os.environ.get('TOKEN_EXPIRATION') or 365 * 24 * 60 * 60
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    CSP_ENABLED = False if os.environ.get("CSP_ENABLED") == 'False' else True
    ACTIVATE_PASSWORD_POLICY = False if os.environ.get('ACTIVATE_PASSWORD_POLICY') == 'False' else True
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE') or 'ru'
    try:
        USER_ACTION_LOGGING_ON_STDOUT = bool(os.environ.get("USER_ACTION_LOGGING_ON_STDOUT")) or True
    except:
        USER_ACTION_LOGGING_ON_STDOUT = True
    USER_ACTION_LOGGING_FILE = os.environ.get("USER_ACTION_LOGGING_FILE") or "logs/user_action.log"
    try:
        FLASK_LOGGING_ON_STDOUT = bool(os.environ.get("FLASK_LOGGING_ON_STDOUT")) or True
    except:
        FLASK_LOGGING_ON_STDOUT = True
    FLASK_LOGGING_FILE = os.environ.get("FLASK_LOGGING_FILE") or "logs/flask.log"
    ERROR_LOGGING_FILE = os.environ.get("ERROR_LOGGING_FILE") or "logs/error.log"
    METASPLOIT_HOST = os.environ.get("METASPLOIT_HOST") or "127.0.0.1"
    METASPLOIT_PORT = os.environ.get("METASPLOIT_PORT") or "55553"
    METASPLOIT_PASSWORD = os.environ.get("METASPLOIT_PASSWORD") or "secret"
    METASPLOIT_VERIFY_SSL = os.environ.get("METASPLOIT_VERIFY_SSL") == "True"
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY") or None
    if VAPID_PRIVATE_KEY is not None:
        try:
            with open(VAPID_PRIVATE_KEY, 'rb') as f:
                VAPID_PRIVATE_KEY = Vapid().from_pem(f.read())
        except Exception as e:
            logger.error(f"Cannot load Vapid private key: {e}")
            sys.exit(1)
    elif os.path.exists(basedir / "vapid.key") and os.path.isfile(basedir / "vapid.key"):
        logger.info(f"Gain vapid key from file {basedir / "vapid.key"}")
        try:
            with open(basedir / "vapid.key", 'rb') as f:
                VAPID_PRIVATE_KEY = Vapid().from_pem(f.read())
        except Exception as e:
            logger.error(f"Cannor load Vapid private key: {e}")
            sys.exit(1)
    else:
        logger.warning("Generate new Vapid private key")
        VAPID_PRIVATE_KEY = Vapid()
        VAPID_PRIVATE_KEY.generate_keys()
        try:
            with open(basedir / "vapid.key", 'wb') as f:
                f.write(VAPID_PRIVATE_KEY.private_pem())
                logger.info(f"Write new Vapid private key into {(basedir / "vapid.key").absolute()}")
        except Exception as e:
            logger.error(f"Exception when write new Vapid private key into {(basedir / "vapid.key").absolute()}: {e}")
            sys.exit(1)
    VAPID_EMAIL = os.environ.get("VAPID_EMAIL") or "your-email@example.com"


class ProductionConfig(DevelopmentConfig):
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex()
    if os.environ.get('SESSION_COOKIE_SECURE') == None:
        SESSION_COOKIE_SECURE = False
    else:
        SESSION_COOKIE_SECURE = bool(os.environ.get('SESSION_COOKIE_SECURE'))
    CSP_ENABLED = True
    try:
        CELERY_WORKERS_COUNT = int(os.environ.get('CELERY_WORKERS_COUNT') or 0)
    except (ValueError, TypeError):
        CELERY_WORKERS_COUNT = 0
    USER_ACTION_LOGGING_FILE = os.environ.get("USER_ACTION_LOGGING_FILE") 
    FLASK_LOGGING_FILE = os.environ.get("FLASK_LOGGING_FILE")
    ERROR_LOGGING_FILE = os.environ.get("ERROR_LOGGING_FILE")


class TestConfig(DevelopmentConfig):
    SECRET_KEY = 'secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str((basedir / 'test_database.db').absolute())
    WTF_CSRF_ENABLED = False