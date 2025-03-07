from flask import Blueprint
from flask_login import login_required


bp = Blueprint('files', __name__, url_prefix='/files')


@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.files.routes
