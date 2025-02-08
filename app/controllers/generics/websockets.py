from app import socketio, db, sanitizer, logger
from app.helpers.general_helpers import authenticated_only
from flask_socketio import emit, join_room, rooms
from app.extensions.moment import moment
from flask import url_for, current_app
from flask_login import current_user
from flask_babel import force_locale, gettext
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
import logging
from sqlalchemy.inspection import inspect
from app.helpers.roles import project_role_can_make_action
from sqlalchemy.inspection import inspect


@socketio.on('join_room', namespace="/generic")
@authenticated_only
def socketio_join_room(data):
    object_name, object_id = data.split(':')
    try:
        obj_class = getattr(models, object_name)
        obj = db.session.scalars(sa.select(obj_class).where(obj_class.id==int(object_id))).one()
    except (AttributeError, TypeError, ValueError, exc.MultipleResultsFound, exc.NoResultFound):
        logger.error(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join unexist generic room: {data}")
        return None
    if not project_role_can_make_action(current_user, obj, 'show_comments'):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join generic room #{data}, in which he has no rights to")
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' was joined to generic room #{data}")
    join_room(data, namespace="/generic")


@socketio.on("add comment", namespace="/generic")
@authenticated_only
def socketio_add_comment(data):
    ''' Trying to add comment, sending in data. Returned True if comment is added and False otherwise '''
    try:
        current_room = rooms()[0]
        obj_class_name, obj_id = current_room.split(':')
        obj_id = int(obj_id)
    except (ValueError, TypeError):
        try:
            current_room = rooms()[1]
            obj_class_name, obj_id = current_room.split(':')
            obj_id = int(obj_id)
        except (ValueError, TypeError):
            logger.error(f"Unknown room:{current_room}. All user rooms: {rooms()}")
            return False
    try:
        obj_class = getattr(models, obj_class_name)
        obj_to_comment = db.session.scalars(sa.select(obj_class).where(obj_class.id == obj_id)).one()
    except (AttributeError, exc.NoResultFound, exc.MultipleResultsFound):
        return False
    if not project_role_can_make_action(current_user, obj_to_comment, 'add_comment'):
        return False
    if 'text' not in data or data['text'] == '':
        return False
    comment = models.Comment(text=sanitizer.sanitize(data["text"]), created_by_id=current_user.id)
    if 'reply_to_id' in data and data['reply_to_id'] != '' and data['reply_to_id'] is not None:
        try:
            rti = db.session.execute(sa.select(models.Comment.id).where(models.Comment.id == int(data["reply_to_id"]))).one()[0]
            comment.reply_to_id = rti
        except (ValueError, TypeError, exc.NoResultFound, exc.MultipleResultsFound) as e:
            logger.error(f'Error when adding a comment. Cannot setting "reply_to_id" with this data: {data}. Error: {e}')
            return None
    try:
        db.session.add(comment)
        obj_to_comment.comments.append(comment)
        if hasattr(obj_to_comment.__class__, 'history'):
            changes = {'changes': [{'action': 'add_comment', 'attrs': {'comment_text': comment.text}}]}
            history_class = inspect(obj_to_comment.__class__).relationships["history"].entity.class_
            hist_elem = history_class(created_by_id=current_user.id, changes=changes)
            obj_to_comment.history.append(hist_elem)
    except AttributeError:
        db.session.rollback()
        return None
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' added a comment #{comment.id}")
    emit('comment added', {'comment_id': comment.id, 'created_by_position': comment.created_by.position.title,
                           'created_by_ava': url_for('files.download_file', file_id=comment.created_by.avatar_id),
                           'created_by': f'<a href="{url_for('users.user_show', user_id=comment.created_by.id)}">{comment.created_by.title}</a> <span class="date">{moment(comment.created_at).fromNow()}</span>',
                           'reply_to_id': comment.reply_to_id, 'text': comment.text},
        namespace='/generic', to=current_room)


@socketio.on('add reaction', namespace="/generic")
@authenticated_only
def socketio_add_reaction(data):
    ''' Trying to add reaction to comment. Emit signal with added reaction '''
    try:
        current_room = rooms()[0]
        obj_class_name, obj_id = current_room.split(':')
        obj_id = int(obj_id)
    except (ValueError, TypeError, IndexError):
        try:
            current_room = rooms()[1]
            obj_class_name, obj_id = current_room.split(':')
            obj_id = int(obj_id)
        except (ValueError, TypeError, IndexError):
            logger.error(f"Unknown room:{current_room}. All user rooms: {rooms()}")
            return None
    try:
        to_comment = db.session.scalars(sa.select(models.Comment).where(models.Comment.id == int(data['comment_id']))).unique().one()
        is_positive = data['is_positive'] == 1
    except (ValueError, TypeError, KeyError, exc.MultipleResultsFound, exc.NoResultFound) as e:
        logger.error(f'Error when adding reaction. No such comment with data: {data}. Error: {e}')
        return None
    if not project_role_can_make_action(current_user, to_comment.to_object, 'add_comment'):
        logger.error(f'Error when adding reaction. This project role cannot make this action!')
        return None
    check = db.session.scalars(sa.select(models.Reaction).where(sa.and_(models.Reaction.created_by_id==current_user.id, models.Reaction.to_comment_id==int(data['comment_id'])))).first()
    if check is not None and check.is_positive == is_positive:
        db.session.delete(check)
        is_positive = None
    elif check is not None:
        check.is_positive = is_positive
    else:
        r = models.Reaction(is_positive=is_positive, created_by_id=current_user.id, to_comment=to_comment)
        db.session.add(r)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' added a reaction #{r.id}")
    emit('reaction added', {'to_comment': to_comment.id, 'positive_count': to_comment.positive_reactions_count(), 'negative_count': to_comment.negative_reactions_count(),
                            'added_by_id': current_user.id, 'is_positive': is_positive}, namespace='/generic', to=current_room)


@socketio.on('get history', namespace='/generic')
@authenticated_only
def get_history_element_via_socketio(data):
    ''' Returned history data via websocket object '''
    try:
        current_room = rooms()[0]
        obj_class_name, obj_id = current_room.split(':')
        obj_id = int(obj_id)
    except (ValueError, TypeError, IndexError):
        try:
            current_room = rooms()[1]
            obj_class_name, obj_id = current_room.split(':')
            obj_id = int(obj_id)
        except (ValueError, TypeError, IndexError):
            logger.error(f"Unknown room:{current_room}. All user rooms: {rooms()}")
            return False
    try:
        by_object_class = getattr(models, obj_class_name)
        by_object = db.session.scalars(sa.select(by_object_class).where(by_object_class.id == obj_id)).one()
    except (AttributeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not hasattr(by_object, 'history') or not project_role_can_make_action(current_user, by_object, 'show_history'):
        return None
    history_class = inspect(by_object_class).relationships.history.entity.class_
    try:
        history_element_id = int(data['id'])
        history_element = db.session.scalars(sa.select(history_class).where(history_class.id == history_element_id)).one()
    except (KeyError, ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound) as e:
        logger.error(f'Error when getting request to get history element, receiving data: {data}, error:{e}')
        return None
    if data.get('locale') not in current_app.config['LANGUAGES']:
        locale = 'en'
    else:
        locale = data.get('locale')
    with force_locale(locale):
        history_data = {'history_text': history_element.as_text(), 'created_at': moment(history_element.created_at).fromNow()}
        if history_element.created_by:
            history_data['created_by_href'] = url_for('users.user_show', user_id=history_element.created_by.id)
            history_data['created_by_title'] = history_element.created_by.title
            history_data['created_by_position'] = history_element.created_by.position.title
            history_data['created_by_avatar'] = url_for('files.download_file', file_id=history_element.created_by.avatar_id)
        else:
            history_data['created_by_href'] = '#'
            history_data['created_by_title'] = gettext("Removed user")
            history_data['created_by_position'] = ''
            history_data['created_by_avatar'] = '#'
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request to object history '{obj_class_name}' #{obj_id}")
        return history_data