from app import socketio, db, logger
from app.helpers.general_helpers import authenticated_only
from app.helpers.projects_helpers import get_current_room
from flask_socketio import emit, join_room
from flask import url_for, current_app
from flask_login import current_user
from app.extensions.moment import moment
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
from app.helpers.roles import project_role_can_make_action


@socketio.on("join_room", namespace="/chats")
@authenticated_only
def join_chats_room(data):
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == int(data))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to connect unexist chat room #{data}")
        return None
    if not project_role_can_make_action(current_user, models.ChatMessage(), 'index', project=project):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to connect chat room #{data}, in which which he has no rights to")
        return None
    join_room(data, namespace="/chats")


@socketio.on('add_comment', namespace='/chats')
@authenticated_only
def add_comment(data):
    cr = get_current_room()
    if cr is None:
        return None
    current_room, current_room_name = cr
    if not project_role_can_make_action(current_user, models.ChatMessage(), 'create', project_id=current_room):
        return None
    cm = models.ChatMessage(created_by=current_user, project_id=current_room, text=data['text'])
    db.session.add(cm)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' add new chat message #{cm.id}' on project #{cm.project_id}")
    emit('create_comment', {'text': data['text'], 'created_by_title': current_user.title, 'created_by_id': current_user.id,
          'created_by_ava': url_for('files.download_file', file_id=current_user.avatar_id), 'created_at': moment(cm.created_at).fromNow()},
          namespace="/chats", to=current_room_name)