from app import socketio, db, logger
from app.helpers.general_helpers import authenticated_only
from app.helpers.projects_helpers import get_current_room
from flask_socketio import emit, join_room
from flask import url_for
from app.helpers.roles import project_role_can_make_action
from flask_login import current_user
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc


@socketio.on('join_room', namespace='/credential')
@authenticated_only
def join_credential_room(data):
    try:
        credential = db.session.scalars(sa.select(models.Credential).where(models.Credential.id == int(data))).one()
    except (exc.MultipleResultsFound, exc.NoResultFound, ValueError, TypeError) as e:
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to join unexist credential room #{data}")
        return None
    if not project_role_can_make_action(current_user, credential, 'show'):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to connect credential room #{data}, in which which he has no rights to")
        return None
    room = data
    join_room(room, namespace="/credential")


@socketio.on('edit related services', namespace='/credential')
@authenticated_only
def edit_related_services(data):
    r = get_current_room()
    if r is None:
        return False
    credential_id, current_room_name = r
    try:
        credential = db.session.scalars(sa.select(models.Credential).where(models.Credential.id == int(credential_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        return None
    if not project_role_can_make_action(current_user, credential, 'update'):
        return None
    try:
        now_services = db.session.scalars(sa.select(models.Service).join(models.Service.host).join(models.Host.from_network)
                                      .where(sa.and_(models.Service.id.in_([int(i) for i in data['related_services']]),
                                                                          models.Network.project_id==credential.project_id))).all()
        updated_services = set(credential.services)
        updated_services = updated_services.union(set(now_services))
        credential.services = now_services
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit related servicees on credential #{credential.id}")
    except (ValueError, TypeError, KeyError):
        return None
    new_services = []
    for i in credential.services:
        ns = {'id': i.id, 'title': i.title, 'ip_address': str(i.host.ip_address), 'port': i.port, 'technical': i.technical}
        ns['transport_level_protocol'] = '' if i.transport_level_protocol is None else i.transport_level_protocol.title
        ns['access_protocol'] = '' if i.access_protocol is None else i.access_protocol.title
        new_services.append(ns)
    emit('change related services', {'rows': new_services},
         namespace='/credential', to=current_room_name)
    for service in updated_services:
        new_credentials = []
        for i in service.credentials:
            nr = {'id': i.id, 'login': i.login, 'password': i.password, 'password_hash': i.password_hash}
            nr['hash_type'] = '' if i.hash_type is None else i.hash_type.title
            new_credentials.append(nr)
        emit('change related credentials', {'rows': new_credentials},
            namespace='/service', to=str(service.id))