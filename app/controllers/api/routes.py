from app import db, logger
from app.controllers.api import bp
from app.models import Project
from flask import request, g
import importlib
import json
from sqlalchemy.inspection import inspect
from app.helpers.api_helpers import error_response, load_from_json, obj_to_json_dict
from .auth import token_auth


@bp.route('/rest/projects/<int:project_id>/<object_name>/index')
@token_auth.login_required
def project_object_index(project_id, object_name):
    if request.content_type == 'application/json':
        try:
            obj = getattr(importlib.import_module('app.models'), object_name)
            limits = int(request.args.get("limits"))
        except AttributeError:
            return error_response(404, "Объекта указанного класса не существует")
        except ValueError:
            return error_response(400, "Неправильно задан параметр limits запроса")
        except TypeError:
            limits = None
        try:
            obj.project_id
        except AttributeError:
            return error_response(400, "Данный объект не связан с проектами")
        project = db.session.get(Project, project_id)
        if limits:
            objs = db.session.scalars(db.select(obj).where(obj.project_id==Project.id).limit(limits))
        else:
            objs = db.session.scalars(db.select(obj).where(obj.project_id==Project.id))
        logger.info(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request all objects '{object_name}' in project '{getattr(project, 'login', 'Not exist')}'")
        return json.dumps({object_name: list(map(lambda x: obj_to_json_dict(x), objs))})
    else:
        return error_response(400, "Неправильно указан заголовок запроса")


@bp.route('/rest/<object_name>/index')
@token_auth.login_required
def object_index(object_name):
    if request.content_type == 'application/json':
        try:
            obj = getattr(importlib.import_module('app.models'), object_name)
            limits = int(request.args.get('limits'))
        except AttributeError:
            logger.warning(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request to get index unexist objects '{object_name}'")
            return error_response(404, "Объекта указанного класса не существует")
        except ValueError:
            return error_response(400, 'Неправильно задан параметр limits запроса')
        except TypeError:
            limits = None
        if limits:
            objs = db.session.scalars(db.select(obj).limit(limits)).all()
        else:
            objs = db.session.scalars(db.select(obj)).all()
        logger.info(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request all objects named '{object_name}'")
        return json.dumps({object_name: list(map(lambda x: obj_to_json_dict(x), objs))})
    else:
        return error_response(400, 'Неправильно указан заголовок запроса')


@bp.route('/rest/<object_name>/<int:object_id>')
@token_auth.login_required
def object_show(object_name, object_id):
    if request.content_type == 'application/json':
        try:
            obj = getattr(importlib.import_module('app.models'), object_name)
        except AttributeError:
            logger.warning(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request to get unexist object '{object_name}'")
            return error_response(404, "Объекта указанного класса не существует")
        ro = db.session.scalars(db.select(obj).where(obj.id==object_id)).first()
        if ro is None:
            logger.warning(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request to get unexist object '{object_name}' #{object_id}")
            return error_response(404, "Объекта с указанным ID не существует")
        logger.info(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request object named '{object_name}' with id '{object_id}'")
        return json.dumps(obj_to_json_dict(ro))
    else:
        return error_response(400, 'Неправильно указан заголовок запроса')


@bp.route('/rest/<object_name>/new', methods=["POST"])
@token_auth.login_required
def object_new(object_name):
    if request.content_type == "application/json":
        try:
            obj = getattr(importlib.import_module('app.models'), object_name)
        except AttributeError:
            logger.warning(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request to create unexist object '{object_name}'")
            return error_response(404, "Объекта указанного класса не существует")
        e = obj()
        db.session.add(e)
        try:
            load_from_json(e, json.loads(request.get_json()), db.session)
            if 'created_by_id' in inspect(e.__class__).column_attrs.keys():
                e.created_by_id = g.current_user.id
            db.session.commit()
            return json.dumps({"status": "success", 'id': e.id})
        except Exception as e:
            return json.dumps({"status": "fail", "error": str(e)})
    else:
        return error_response(400, "Неправильно указан заголовок запроса")


@bp.route('/rest/<object_name>/<int:object_id>', methods=["PUT"])
@token_auth.login_required
def object_edit(object_name, object_id):
    if request.content_type == "application/json":
        try:
            obj_class = getattr(importlib.import_module('app.models'), object_name)
        except AttributeError:
            logger.warning(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request to edit unexist object '{object_name}'")
            return error_response(404, 'Объект указанного класса не существует')
        obj = db.session.scalars(db.select(obj_class).where(obj_class.id==object_id)).first()
        if obj is None:
            logger.warning(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request to edit unexist object '{object_name}' #{object_id}")
            return error_response(404, "Объекта с указанным ID не существует")
        try:
            load_from_json(obj, json.loads(request.get_json()), db.session)
            if 'updated_by_id' in inspect(obj.__class__).column_attrs.keys():
                obj.updated_by_id = g.current_user.id
            db.session.commit()
            logger.info(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' edit object '{object_name}' #{object_id}")
            return json.dumps({"status": "success", 'id': obj.id})
        except Exception as e:
            return json.dumps({"status": "fail", "error": str(e)})
    else:
        return error_response(400, 'Неправильно указан заголовок запроса')


@bp.route('/rest/<object_name>/<int:object_id>', methods=["DELETE"])
@token_auth.login_required
def object_delete(object_name, object_id):
    if request.content_type == "application/json":
        try:
            obj_class = getattr(importlib.import_module('app.models'), object_name)
        except AttributeError:
            logger.warning(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request to delete unexist object '{object_name}'")
            return error_response(404, 'Объект указанного класса не существует')
        obj = db.session.scalars(db.select(obj_class).where(obj_class.id==object_id)).first()
        if obj is None:
            logger.warning(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' request to delete unexist object '{object_name}' #{object_id}")
            return error_response(404, 'Объекта с указанным ID не существует')
        db.session.delete(obj)
        db.session.commit()
        logger.info(f"User '{getattr(g.current_user, 'login', 'Anonymous')}' delete object '{object_name}' #{object_id}")
        return json.dumps({"status": "success"})
    else:
        return error_response(400, 'Неправильно указан заголовок запроса')
