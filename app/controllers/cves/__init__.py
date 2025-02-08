from flask import Blueprint

bp = Blueprint('cves', __name__, url_prefix='/cves')


import app.controllers.cves.routes
