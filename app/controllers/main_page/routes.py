from app import db, logger
from app.controllers.main_page import bp
from flask import render_template, current_app, request, jsonify, send_from_directory
from flask_login import current_user
from app.helpers.main_page_helpers import DefaultEnvironment


@bp.route('/')
def main_page():
    ctx = DefaultEnvironment('main_page', 'show')()
    context = {'global_settings': current_app.config["GlobalSettings"]}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' required main page")
    return render_template('main_page/index.html', **ctx, **context)


@bp.route('/sw.js')
def service_worker():
    return send_from_directory(current_app.static_folder, 'js/webpush_service_worker.js', mimetype='application/javascript')


@bp.route('/subscribe', methods=['POST'])
def subscribe_webpush():
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' required subscribe to WebPush notifications")
    sub_info = request.get_json()
    if current_user.is_authenticated:
        current_user.subscription_info = sub_info
        current_user.webpush_enabled = True
        db.session.commit()
    return jsonify({'status': 'success'})


@bp.route('/unsubscribe', methods=["POST"])
def unsubscribe_webpush():
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' required unsubscribe from WebPush notifications")
    if current_user.is_authenticated:
        current_user.webpush_enabled = False
        db.session.commit()
    return jsonify({'status': 'success'})

