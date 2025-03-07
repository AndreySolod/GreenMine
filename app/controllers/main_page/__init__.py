from flask import Blueprint
from flask_login import login_required


bp = Blueprint('main_page', __name__, url_prefix='/')


@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.main_page.routes
