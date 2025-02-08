from flask import Blueprint


bp = Blueprint('wiki_pages', __name__, url_prefix='/wiki')


import app.controllers.wiki_pages.routes
