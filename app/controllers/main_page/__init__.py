from flask import Blueprint


bp = Blueprint('main_page', __name__, url_prefix='/')


import app.controllers.main_page.routes
