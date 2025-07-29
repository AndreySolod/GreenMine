from app import db, logger
import app.models as models
import functools
from flask_login import current_user
from flask import abort
from typing import List
import sqlalchemy as sa


class UserRole:
    title: str
    description: str
    
    def calc(user: models.User, current_object) -> bool:
        ''' Представляет из себя функцию, предназначенную для определения - имеет ли данный пользователь данную роль относительно данного объекта '''
        raise NotImplementedError()


def administrator_only(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if not current_user.is_anonymous and current_user.position.is_administrator:
            return func(*args, **kwargs)
        abort(403)
    return wrapped


def has_user_role(role_list: List, obj) -> bool:
    if current_user.is_anonymous:
        return False # Пользователь ещё не вошёл в систему
    if current_user.position.is_administrator:
        return True # Администратор обладает всеми ролями
    has_role = False
    for role in role_list:
        if role.calc(current_user, obj):
            has_role = True
            break
    return has_role


def only_for_roles(role_list : List, obj):
    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            has_role = has_user_role(role_list, obj)
            if not has_role:
                abort(403)
            return func(*args, **kwargs)
        return wrapped
    return decorator


def project_role_can_make_action(user: models.User, obj, action: str, **kwargs) -> bool:
    ''' For gained current user, object on project and action check permissions - can user make this action, and return true if yes and False otherwise '''
    if not hasattr(obj, 'project') and obj.__class__.__name__ != 'Project' and not 'project_id' in kwargs and not 'project' in kwargs:
        raise ValueError("Current object isn't assign to project!")
    if obj.__class__.__name__ == 'Project':
        project_id = obj.id
    elif 'project_id' in kwargs:
        project_id = kwargs['project_id']
    elif 'project' in kwargs:
        project_id = kwargs['project'].id
    else:
        project_id = obj.project.id
    # check that action is exist in Meta information in object
    if not action in obj.Meta.project_permission_actions.keys():
        raise ValueError(f'Action {action} on object {obj.__class__.__name__} is not registered!')
    if 'project' in kwargs:
        project = kwargs['project']
    else:
        project = db.session.scalars(sa.select(models.Project).where(models.Project.id == project_id)).one()
    if has_user_role([ProjectManager], project): # ProjectManager has all rights to project
        return True
    # all current user roles on project
    all_roles = db.session.scalars(sa.select(models.UserRoleHasProject.role_id).where(sa.and_(models.UserRoleHasProject.user_id == user.id,
                                                                                      models.UserRoleHasProject.project_id == project_id))).all()
    if len(all_roles) == 0:
        all_roles = db.session.scalars(sa.select(models.ProjectRole.id).where(models.ProjectRole.string_slug == 'anonymous')).all()
    granted_actions = db.session.scalars(sa.select(models.RoleHasProjectObjectAction.is_granted).where(sa.and_(models.RoleHasProjectObjectAction.role_id.in_(all_roles),
                                                                                                               models.RoleHasProjectObjectAction.object_class_name == obj.__class__.__name__,
                                                                                                               models.RoleHasProjectObjectAction.action == action,
                                                                                                               models.RoleHasProjectObjectAction.is_granted == True))).first()
    return granted_actions is not None


def project_role_can_make_action_or_abort(user: models.User, obj, action: str, **kwargs) -> None:
    ''' Check if current user can make action on current object on project and aborted with 403 error if they can't '''
    if not project_role_can_make_action(user, obj, action, **kwargs):
        if obj.__class__.__name__ == 'DefaultMeta':
            class_name = obj.__name__
            obj_id = "None"
            project_id = kwargs.get('project_id') or getattr(kwargs.get('project'), 'id', 'None')
        else:
            class_name = obj.__class__.__name__
            obj_id = obj.id
            project_id = kwargs.get('project_id') or getattr(kwargs.get('project'), 'id', 'None')
        logger.warning(f"User '{getattr(user, 'title', 'Anonymous')}' trying to exist action '{action}' on object {class_name} with id=#{obj_id} on project '{project_id}' which he has no rights to")
        abort(403)


class UserHimself(UserRole):
    title = 'Сам пользователь'
    description = 'Если пользователь смотрит на свою карточку, то он обладает этой ролью. В противном случае - нет'

    def calc(user: models.User, current_object) -> bool:
        if isinstance(current_object, models.User):
            return user.position.is_administrator or current_object.id == user.id
        return False
    

class ProjectManager(UserRole):
    title = 'Руководитель проекта'
    description = 'Человек, указанный как руководитель проекта'

    def calc(user: models.User, current_object) -> bool:
        if hasattr(current_object, 'project'):
            return current_object.project.leader_id == user.id
        elif current_object.__class__.__name__ == 'Project':
            return current_object.leader_id == user.id
        return False