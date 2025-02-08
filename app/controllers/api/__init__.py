from flask import Blueprint


bp = Blueprint('api', __name__, url_prefix='/api')


import app.controllers.api.routes
