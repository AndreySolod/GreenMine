from app import socketio, db, sanitizer, logger
from app.helpers.general_helpers import authenticated_only
from app.helpers.projects_helpers import get_current_room
from flask_socketio import emit, join_room
from flask import url_for, current_app
from app.helpers.roles import project_role_can_make_action
from flask_login import current_user
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
from flask_babel import gettext, force_locale


@socketio.on("join_room", namespace="/user")
@authenticated_only
def join_task_room(data):
    try:
        user = db.session.scalars(sa.select(models.User).where(models.User.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError):
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect user room {data}")
        return None
    if current_user.id != int(data):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join user room #{data}, in which he has no rights to")
        return None
    room = data
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join user room #{data}")
    join_room(room, namespace="/user")


@socketio.on("get notification", namespace="/user")
@authenticated_only
def get_user_notification(data):
    r = get_current_room()
    if r is None:
        return False
    user_id, current_room_name = r
    try:
        notification = db.session.scalars(sa.select(models.UserNotification).where(models.UserNotification.id == int(data['notification_id']))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if notification.to_user_id != current_user.id:
        return None
    if data['lang'] in current_app.config['LANGUAGES']:
        lang = data['lang']
    else:
        lang = 'en'
    with force_locale(lang):
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' requested new notification #{notification.id}")
        return {'link': notification.link_to_object, 'by_user': notification.by_user.title, 'description': sanitizer.sanitize(gettext(notification.description, **notification.technical_info))}


@socketio.on('toggle sidebar', namespace="/user")
@authenticated_only
def user_toggle_sidebar():
    r = get_current_room()
    if r is None:
        return None
    current_user.environment_setting.sidebar_hide = not current_user.environment_setting.sidebar_hide
    db.session.commit()
