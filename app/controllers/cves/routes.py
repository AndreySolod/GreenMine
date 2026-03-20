from flask import render_template, abort, redirect, url_for, flash, request, jsonify, current_app
from flask_login import current_user
from app.controllers.cves import bp
from app.models import CriticalVulnerability, ProgrammingLanguage, VulnerableEnvironmentType
from app import db, side_libraries, logger
from app.helpers.general_helpers import get_or_404, get_bootstrap_table_json_data, BootstrapTableSearchParams
from app.helpers.main_page_helpers import DefaultEnvironment
from .forms import CriticalVulnerabilityCreateForm, CriticalVulnerabilityEditForm
import json
from flask_babel import lazy_gettext as _l
from app.helpers.roles import user_position_can_make_action_or_abort
import sqlalchemy as sa
import sqlalchemy.exc as exc


@bp.route('/index')
def cve_index():
    user_position_can_make_action_or_abort(current_user, CriticalVulnerability, 'index')
    filters = {}
    for obj in [VulnerableEnvironmentType, ProgrammingLanguage]:
        now_obj = {}
        for i, t in db.session.execute(db.select(obj.id, obj.title)):
            now_obj[i] = t
        filters[obj.__name__] = json.dumps(now_obj)
    ctx = DefaultEnvironment('CriticalVulnerability', 'index')()
    side_libraries.library_required('bootstrap_table')
    return render_template('cves/index.html', **ctx, filters=filters)


@bp.route('/index-data')
def cve_index_data():
    user_position_can_make_action_or_abort(current_user, CriticalVulnerability, 'index')
    additional_params: BootstrapTableSearchParams = {'obj': CriticalVulnerability,
                                                     'column_index': ['id', 'title', 'description', 'vulnerable_environment_type', 'proof_of_concept_language'],
                                                     'base_select': lambda x: x.where(CriticalVulnerability.archived == False)}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all cves")
    return get_bootstrap_table_json_data(request, additional_params)
        


@bp.route('/new', methods=["GET", "POST"])
def cve_new():
    user_position_can_make_action_or_abort(current_user, CriticalVulnerability, 'create')
    form = CriticalVulnerabilityCreateForm(db.session)
    if form.validate_on_submit():
        cve = CriticalVulnerability()
        form.populate_obj(db.session, cve, current_user)
        db.session.add(cve)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new cve #{cve.id}")
        flash(_l("Critical vulnerability has been successfully added"), 'success')
        return redirect(url_for('cves.cve_show', cve_id=cve.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, CriticalVulnerability)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('CriticalVulnerability', 'new')()
    return render_template('cves/new.html', **ctx, form=form)


@bp.route('/<cve_id>/edit', methods=["GET", "POST"])
def cve_edit(cve_id):
    user_position_can_make_action_or_abort(current_user, CriticalVulnerability, 'update')
    try:
        cve_id = int(cve_id)
    except (ValueError, TypeError):
        abort(404)
    cve = get_or_404(db.session, CriticalVulnerability, cve_id)
    form = CriticalVulnerabilityEditForm(db.session)
    if form.validate_on_submit():
        form.populate_obj(db.session, cve)
        cve.updated_by_id = current_user.id
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit cve #{cve.id}")
        flash(_l("Critical vulnerability has been successfully updated"), 'success')
        return redirect(url_for('cves.cve_show', cve_id=cve.id))
    elif request.method == 'GET':
        form.load_exist_value(cve)
    ctx = DefaultEnvironment('CriticalVulnerability', 'edit', obj_val=cve)()
    context = {'form': form}
    return render_template('cves/new.html', **context, **ctx)


@bp.route('/<cve_id>/show')
def cve_show(cve_id):
    user_position_can_make_action_or_abort(current_user, CriticalVulnerability, 'show')
    try:
        cve_id = int(cve_id)
    except (ValueError, TypeError):
        abort(404)
    cve = get_or_404(db.session, CriticalVulnerability, cve_id)
    ctx = DefaultEnvironment('CriticalVulnerability', 'show', obj_val=cve)()
    side_libraries.library_required('ckeditor')
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request cve #{cve.id}")
    return render_template('cves/show.html', **ctx, cve=cve)


@bp.route('/<cve_id>/delete', methods=["POST", 'DELETE'])
def cve_delete(cve_id):
    user_position_can_make_action_or_abort(current_user, CriticalVulnerability, 'delete')
    try:
        cve_id = int(cve_id)
    except (ValueError, TypeError):
        abort(404)
    cve = get_or_404(db.session, CriticalVulnerability, cve_id)
    db.session.delete(cve)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete cve #{cve_id}")
    flash(_l("Critical vulnerability has been successvully deleted"), 'success')
    return redirect(url_for('cves.cve_index'))


@bp.route('/cvss-by-cve/<cve_id>')
def get_issue_cvss_by_cve(cve_id: str):
    try:
        cve = db.session.scalars(sa.select(CriticalVulnerability).where(CriticalVulnerability.id == int(cve_id))).one()
    except (ValueError, TypeError, exc.MultipleResultsFound, exc.NoResultFound):
        logger.warning("Erorr when trying to obtain cvss by cve_id")
        abort(400)
    return jsonify({'cvss': cve.cvss})


@bp.route('get-cve-select2-data')
def get_cve_select2_data():
    try:
        page = int(request.args.get('page'))
    except TypeError:
        page = 1
    except ValueError:
        abort(400)
    user_position_can_make_action_or_abort(current_user, CriticalVulnerability, 'index')
    query = request.args.get('term') if request.args.get('term') else ''
    data = db.session.scalars(sa.select(CriticalVulnerability).where(CriticalVulnerability.title.ilike('%' + query + '%'))
                                        .limit(current_app.config["GlobalSettings"].pagination_element_count_select2 + 1)
                                        .offset((page - 1) * current_app.config["GlobalSettings"].pagination_element_count_select2)).all()
    more = len(data) == current_app.config["GlobalSettings"].pagination_element_count_select2 + 1
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request critical vulnerability via select2-data")
    result = {'results': [{'id': i.id, 'text': i.title} for i in data[:min(len(data), current_app.config["GlobalSettings"].pagination_element_count_select2):]], 'pagination': {'more': more}}
    return jsonify(result)