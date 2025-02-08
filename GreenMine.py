#!/usr/bin/env python

from app import create_app, cli
import logging
import config
import os


env_type = os.environ.get("ENVIRONMENT") or 'DEVELOP'
default_host = os.environ.get('APP_HOST') or '0.0.0.0'
try:
    default_port = int(os.environ.get("APP_PORT")) or 5000
except (ValueError, TypeError):
    default_port = 5000
if env_type == 'DEVELOP':
    debug = True
    app = create_app(config_class=config.DevelopmentConfig, debug=debug)
else:
    debug = False
    app = create_app(config_class=config.ProductionConfig, debug=debug)
cli.register(app)


def create_gunicorn_app():
    app.setting_custom_attributes_for_application()
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Run application
    app.run(host=default_host, port=default_port, debug=debug)
