from flask import Blueprint


bp = Blueprint('users', __name__, url_prefix='/users')


import app.controllers.users.routes
import app.controllers.users.websockets
import app.controllers.users.ajax_routes