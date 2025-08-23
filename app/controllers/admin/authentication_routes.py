from app import db, logger
from app.controllers.admin import bp
import app.models as models
from app.helpers.admin_helpers import DefaultEnvironment
import sqlalchemy as sa
import sqlalchemy.exc as exc
import app.controllers.admin.authentication_forms as forms
from flask import redirect, abort, url_for, render_template, current_app, flash, request, current_app
from flask_babel import lazy_gettext as _l


@bp.route('/authentication/parameters', methods=["GET", "POST"])
def authentication_password_policy_settings():
    try:
        gs = db.session.scalars(sa.select(models.GlobalSettings)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        logger.error("Error: There are 2 instances of Global Settings")
        abort(500)
    form = forms.AuthenticationParametersForm()
    if form.validate_on_submit():
        form.populate_obj(db.session, gs)
        db.session.add(gs)
        db.session.commit()
        db.session.refresh(gs)
        db.session.expunge(gs)
        current_app.config["GlobalSettings"] = gs
        if gs.authentication_method == models.AuthenticationMethod.PASSWORD:
            current_app.password_policy_manager.activate = True
        else:
            current_app.password_policy_manager.activate = False
        flash(_l("Password policy settings have been successfully updated"), 'success')
        return redirect(url_for('admin.authentication_password_policy_settings'))
    elif request.method == 'GET':
        form.load_exist_value(gs)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment()()
    return render_template('admin/authentication_settings.html', **ctx, form=form, global_settings=current_app.config["GlobalSettings"])