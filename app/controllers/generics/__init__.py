from flask import Blueprint


bp = Blueprint('generic', __name__, url_prefix='/generic')


import app.controllers.generics.routes
import app.controllers.generics.websockets