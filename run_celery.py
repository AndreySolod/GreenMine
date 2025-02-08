#!/usr/bin/env python
from app import create_app, celery
from config import DevelopmentConfig
from app.extensions.celery import CeleryManager


flask_app = create_app(DevelopmentConfig)
celery.init_app(flask_app)

if __name__ == '__main__':
    celery.start()
