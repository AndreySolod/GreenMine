from flask import Blueprint
from flask_login import login_required


bp = Blueprint('generic', __name__, url_prefix='/generic')


import app.controllers.generics.routes
import app.controllers.generics.websockets