from flask import Blueprint
from flask_login import login_required

bp = Blueprint('cves', __name__, url_prefix='/cves')


@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.cves.routes
