from flask import Blueprint


bp = Blueprint('files', __name__, url_prefix='/files')


import app.controllers.files.routes
