from flask import Blueprint
from flask_login import login_required


bp = Blueprint('wiki_pages', __name__, url_prefix='/wiki')


@bp.before_request
@login_required
def check_login_required():
    pass


import app.controllers.wiki_pages.routes
