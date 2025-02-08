import flask_httpauth
from flask import g, jsonify
from app import db, logger
from app.models import User
from app.helpers.api_helpers import error_response
from app.controllers.api import bp


basic_auth = flask_httpauth.HTTPBasicAuth()
token_auth = flask_httpauth.HTTPTokenAuth(scheme='Bearer')


@basic_auth.verify_password
def verify_password(login, password):
    u = db.session.scalars(db.select(User).where(User.login==login)).first()
    if u is None:
        return False
    g.current_user = u
    password_valid = u.check_password(password)
    if password_valid:
        logger.info(f"User '{u.login}' authenticate via API with valid password")
    else:
        logger.info(f"User '{u.login}' trying to authenticate via API, but password is invalid")
    return password_valid


@basic_auth.error_handler
def basic_auth_error():
    return error_response(401)


@bp.route('/tokens', methods=["POST"])
@basic_auth.login_required
def get_token():
    token = g.current_user.get_token()
    logger.info(f"User '{g.current_user.login}' request a new token to API")
    return jsonify({'token': token})


@token_auth.verify_token
def verify_token(token):
    g.current_user = User.check_token(token) if token else None
    return g.current_user is not None


@token_auth.error_handler
def token_auth_error():
    return error_response(401)


@bp.route('/tokens', methods=["DELETE"])
@token_auth.login_required
def revoke_token():
    g.current_user.revoke_token()
    logger.info(f"User '{g.current_user.login}' request to delete an API token")
    return '', 204
