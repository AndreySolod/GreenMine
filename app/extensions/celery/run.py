from app import create_app, celery
from config import Config
from app.extensions.celery import CeleryManager


flask_app = create_app(Config)
celery.init_app(flask_app)

if __name__ == '__main__':
    celery.start()