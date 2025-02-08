from app import socketio, db, sanitizer, logger
from app.helpers.general_helpers import authenticated_only, utcnow
from app.helpers.projects_helpers import get_current_room
from flask_socketio import emit, join_room
from flask import url_for, current_app
from flask_login import current_user
from app.extensions.moment import moment
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
from app.helpers.roles import project_role_can_make_action


@socketio.on("join_room", namespace="/notes")
@authenticated_only
def join_notes_room(data):
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == int(data))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join incorrect notes room {data}")
        return None
    if not project_role_can_make_action(current_user, models.Note(), 'index', project=project):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join notes room #{data}, in which he has no rights to")
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' join notes room #{data}")
    join_room(data, namespace="/notes")


@socketio.on("edit_note", namespace="/notes")
@authenticated_only
def socketio_edit_note(data):
    cr = get_current_room()
    if cr is None:
        return None
    _, current_room_name = cr
    try:
        note = db.session.get(models.Note, int(data['note_id']))
        if not project_role_can_make_action(current_user, note, 'update'):
            return None
        note.updated_at = utcnow()
        note.updated_by_id = current_user.id
        note.title = sanitizer.escape(data["note_title"], models.Note.title.type.length)
        note.description = sanitizer.sanitize(data['note_description'])
        imp = db.session.scalars(sa.select(models.NoteImportance).where(models.NoteImportance.id == int(data['note_importance']))).one()
        note.importance = imp
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to edit note #{data['note_id']} with error paramethers")
        return None
    db.session.add(note)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit note #{note.id}")
    emit('note edited', {'note_id': note.id, 'title': note.title, 'description': note.description, 'importance_id': note.importance.id,
                       'importance_title': note.importance.title, 'importance_color': note.importance.color,
                       'user_href': url_for('users.user_show', user_id=note.updated_by_id), 'user_title': note.updated_by.title,
                       'updated_at': moment(note.updated_at).fromNow()},
                         namespace='/notes', to=current_room_name)


@socketio.on('create note', namespace='/notes')
@authenticated_only
def socketio_create_note(data):
    cr = get_current_room()
    if cr is None:
        return None
    current_room, current_room_name = cr
    try:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == current_room)).one()
        if not project_role_can_make_action(current_user, models.Note(), 'create', project=project):
            return None
        importance = db.session.scalars(sa.select(models.NoteImportance).where(models.NoteImportance.id == int(data['importance_id']))).one()
        print('importance finding')
        note = models.Note(title=sanitizer.escape(data['title'], models.Note.title.type.length), description=sanitizer.sanitize(data['description']), importance=importance, project=project, created_by=current_user)
        db.session.add(note)
        db.session.commit()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound) as e:
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to create note with error paramethers. Error: {e}")
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create note #{note.id}")
    emit('note created', {'note_id': note.id, 'title': note.title, 'description': note.description, 'importance_id': note.importance.id,
                          'importance_title': note.importance.title, 'importance_color': note.importance.color,
                          'user_href': url_for('users.user_show', user_id=note.created_by_id), 'user_title': note.created_by.title,
                          'created_at': moment(note.created_at).fromNow()},
                          namespace='/notes', to=current_room_name)