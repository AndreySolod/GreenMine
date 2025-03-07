from app import db, logger
from app.controllers.main_page import bp
from flask import render_template, current_app
from flask_login import current_user
from app.helpers.main_page_helpers import DefaultEnvironment


@bp.route('/')
def main_page():
    ctx = DefaultEnvironment('main_page', 'show')()
    context = {'global_settings': current_app.config["GlobalSettings"]}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' required main page")
    return render_template('main_page/index.html', **ctx, **context)
