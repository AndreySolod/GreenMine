import json
import importlib
import app.models as models
import app.controllers.admin.issue_template_forms as issue_template_forms
from flask import render_template, flash, redirect, url_for, request, abort, jsonify, current_app
from flask_login import current_user
from app.controllers.admin import bp
from app import db, side_libraries, logger
from app.helpers.general_helpers import get_or_404, find_data_by_request_params
from app.helpers.admin_helpers import get_enumerated_objects, DefaultEnvironment, get_status_objects
import sqlalchemy as sa
from sqlalchemy import exc
from sqlalchemy import func
from sqlalchemy.inspection import inspect
from .forms import get_object_create_form, get_object_edit_form, get_status_transit_form
from . import main_settings_forms
from flask_babel import lazy_gettext as _l


@bp.route('/')
@bp.route('/index')
def index():
    ''' Displayed a list of admin tools '''
    ctx = DefaultEnvironment('index')()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' get index page")
    return render_template('admin/index.html', **ctx)


@bp.route('/index/edit', methods=["GET", "POST"])
def admin_main_info_edit():
    ''' Edit main information about application '''
    if request.method == 'POST':
        if 'edit_elem' not in request.args:
            abort(400)
        elem = request.args.get('edit_elem')
        if elem == 'main_page_name':
            if 'main_page_name' in request.values:
                main_page_name = request.values.get('main_page_name')
                if main_page_name is None or len(main_page_name) > models.GlobalSettings.main_page_name.type.length:
                    abort(400)
                try:
                    gs = db.session.scalars(sa.select(models.GlobalSettings)).one()
                except (exc.NoResultFound, exc.MultipleResultsFound):
                    current_app.logger.error("Error: There are 2 instances of Global Settings")
                    abort(500)
                gs.main_page_name = main_page_name
                db.session.add(gs)
                db.session.commit()
                logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' updated main page name")
                current_app.config["GlobalSettings"].main_page_name = main_page_name
                return jsonify({"status": "success"})
            abort(400)
        elif elem == 'text_main_page':
            text_form = main_settings_forms.MainPageTextForm()
            if text_form.validate_on_submit():
                try:
                    gs = db.session.scalars(sa.select(models.GlobalSettings)).one()
                except (exc.NoResultFound, exc.MultipleResultsFound):
                    current_app.logger.error("Error: There are 2 instances of Global Settings")
                    abort(500)
                gs.text_main_page = text_form.text_main_page.data
                db.session.add(gs)
                db.session.commit()
                logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' updated main page text")
                current_app.config["GlobalSettings"].text_main_page = text_form.text_main_page.data
                return redirect(url_for('admin.admin_main_info_edit'))
            abort(400)
        elif elem == 'main_parameters':
            main_parameters_form = main_settings_forms.MainParameterForm()
            if main_parameters_form.validate_on_submit():
                try:
                    gs = db.session.scalars(sa.select(models.GlobalSettings)).one()
                except (exc.MultipleResultsFound, exc.NoResultFound):
                    current_app.logger.error("Error: There are 2 instances of Global Settings")
                    abort(500)
                gs.default_language_id = main_parameters_form.default_language.data
                gs.m2m_join_symbol = main_parameters_form.m2m_join_symbol.data
                gs.m2m_max_items = int(main_parameters_form.m2m_max_items.data)
                gs.pagination_element_count_select2 = int(main_parameters_form.pagination_element_count_select2.data)
                db.session.add(gs)
                db.session.commit()
                db.session.refresh(gs)
                db.session.expunge(gs)
                current_app.config["GlobalSettings"] = gs
            return redirect(url_for('admin.admin_main_info_edit'))
        else:
            abort(404)
    name_form = main_settings_forms.MainPageNameForm()
    text_form = main_settings_forms.MainPageTextForm()
    name_form.main_page_name.data = current_app.config["GlobalSettings"].main_page_name
    text_form.text_main_page.data = current_app.config["GlobalSettings"].text_main_page
    main_parameters_form = main_settings_forms.MainParameterForm()
    main_parameters_form.load_exist_value(current_app.config["GlobalSettings"])
    ctx = DefaultEnvironment('admin_main_info_edit')()
    context = {'global_settings': current_app.config["GlobalSettings"], "name_form": name_form, "text_form": text_form,
               'main_parameters_form': main_parameters_form}
    return render_template('admin/main_settings_edit.html', **ctx, **context)


@bp.route('/objects/index')
def object_index():
    ''' Handles paths for enumeration classes. In general, it just returns a page with a list of all possible enumeration objects. '''
    objs = get_enumerated_objects()
    ctx = DefaultEnvironment('object_index')()
    side_libraries.library_required('bootstrap_table')
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' requested all enumerated object index")
    return render_template('admin/object_index.html', objs=objs, **ctx)


@bp.route('/objects/<object_type>/index-data')
def object_type_index_data(object_type):
    try:
        obj_type = getattr(importlib.import_module('app.models'), object_type)
    except AttributeError:
        abort(404)
    if obj_type not in get_enumerated_objects():
        abort(400)
    sql, sql_count = find_data_by_request_params(obj_type, request)
    objs = db.session.scalars(sql).all()
    total = db.session.scalars(sql_count).one()
    attr_name = [i.name for i in inspect(obj_type).columns if not i.name.endswith('_id')]
    attr_name += [i.key for i in inspect(obj_type).relationships]
    simple_names = [i.name for i in inspect(obj_type).columns]
    rows = []
    for i in objs:
        now_obj = {}
        for attr in attr_name:
            na = getattr(i, attr)
            if attr in simple_names or na is None:
                now_obj[attr] = na
            elif isinstance(na, list) or isinstance(na, set):
                now_obj[attr] = ';'.join([i.title for i in na][:7:])
                if len(na) > 7:
                    now_obj[attr] += f';Total {len(na)} elements'
            else:
                added = False
                for ci in obj_type.Meta.column_index:
                    if '.' in ci and attr == ci.split('.')[0]:
                        now_obj[ci] = na.title
                        added = True
                        break
                if not added:
                    now_obj[attr + ".title-input"] = na.title
        rows.append(now_obj)
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' requested all enumerated object '{object_type}'")
    return jsonify({'total': total, 'rows': rows})


@bp.route('/objects/<object_type>/index')
def object_type_index(object_type):
    ''' Processes paths for a specific enumeration class - possible enumeration options are displayed,
        as well as buttons for adding and editing an enumeration. '''
    try:
        obj_type = getattr(importlib.import_module('app.models'), object_type)
    except AttributeError:
        abort(404)
    if obj_type not in get_enumerated_objects():
        abort(400)
    ctx = DefaultEnvironment('object_type_index', obj_type)()
    attr_name = [] # Attribute titles. Substituted in the data-field
    attr_field_types = [] # Attribute types. Substituted in the data-filter-control
    attr_field_values = [] # Possible values for fields of the type select
    attr_titles = [] # Attribute values are already labels, and are header values
    column_index = obj_type.Meta.column_index
    for i in inspect(obj_type).columns: # First we add all the simple attributes
        if not i.name.endswith('_id'):
            attr_name.append(i.name)
            attr_titles.append(i.info["label"])
            attr_field_types.append('input')
            attr_field_values.append(None)
    for i in inspect(obj_type).relationships: # Now we add all complex attributes
        attr_titles.append(i.info["label"])
        added = False
        for ci in column_index:
            if '.' in ci and i.key == ci.split('.')[0]:
                attr_name.append(ci)
                attr_field_types.append(ci.split('-')[1])
                field_values = json.dumps({i[0]: i[0] for i in db.session.execute(db.select(i.entity.class_.title)).all()})
                attr_field_values.append(field_values)
                added = True
                break
        if not added: # This means that the specified attribute is not in column_index. Add it as an object of type "input"
            if not i.uselist:
                attr_name.append(i.key + ".title-input")
                attr_field_types.append('input')
                attr_field_values.append(None)
            else:
                attr_name.append(i.key)
                attr_field_types.append(None)
                attr_field_values.append(None)
    side_libraries.library_required('bootstrap_table')
    side_libraries.library_required('contextmenu')
    return render_template('admin/object_type_index.html', **ctx,
                           attrs=list(zip(attr_name, attr_titles, attr_field_types, attr_field_values)),
                           object_type=object_type)


@bp.route('/objects/<object_type>/new', methods=['GET', "POST"])
def object_type_new(object_type):
    ''' Handle path for new enumeration object  '''
    try:
        obj_type = getattr(importlib.import_module('app.models'), object_type)
    except AttributeError:
        abort(404)
    if obj_type not in get_enumerated_objects():
        abort(400)
    form = get_object_create_form(obj_type, db.session)()
    form_attributes = [getattr(form, i) for i in form.inspected_columns]
    form_attrs = []
    for i in form_attributes:
        form_attrs.append((i, i.__class__.__name__=='BooleanField'))
    if form.validate_on_submit():
        o = obj_type()
        form.populate_obj(db.session, o, current_user)
        try:
            db.session.add(o)
            db.session.commit()
        except Exception as e:
            flash(_l("Error when create object: %(error)s. Try again", error=str(e)))
            db.session.rollback()
        else:
            flash(_l('Object «%(title)s» successfully added', title=o.title), 'success')
            logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new enumerated object '{object_type}' #{o.id}: '{o.title}")
            return redirect(url_for('admin.object_type_index', object_type=object_type))
    elif request.method == 'GET':
        form.load_default_data(db.session, obj_type)
    ctx = DefaultEnvironment('object_type_new', obj_type)()
    return render_template('admin/object_type_new.html', form=form,
                           form_attrs=form_attrs, **ctx)


@bp.route('/objects/<object_type>/<object_id>/edit', methods=['GET', "POST"])
def object_type_edit(object_type, object_id):
    try:
        obj_type = getattr(importlib.import_module('app.models'), object_type)
        object_id = int(object_id)
    except AttributeError:
        abort(404)
    except (ValueError, TypeError):
        abort(400)
    if obj_type not in get_enumerated_objects():
        abort(400)
    try:
        obj = db.session.scalars(sa.select(obj_type).where(obj_type.id==object_id)).one()
    except exc.NoResultFound:
        abort(404)
    form = get_object_edit_form(obj_type, db.session)()
    form_attributes = [getattr(form, i) for i in form.inspected_columns]
    form_attrs = []
    for i in form_attributes:
        form_attrs.append((i, i.__class__.__name__=='BooleanField'))
    if form.validate_on_submit():
        form.populate_obj(db.session, obj)
        try:
            db.session.add(obj)
            db.session.commit()
        except Exception as e:
            flash(_l("Error when create object: %(error)s. Try again", error=str(e)))
            db.session.rollback()
        else:
            logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit enumerated object '{object_type}' #{obj.id}: '{obj.title}'")
            flash(_l('Object «%(title)s» edited successfully', title=obj.title), 'success')
            return redirect(url_for('admin.object_type_index', object_type=object_type))
    elif request.method == 'GET':
        form.load_exist_value(obj)
    ctx = DefaultEnvironment('object_type_index', obj_type)()
    return render_template('admin/object_type_new.html', form=form,
                           form_attrs=form_attrs, **ctx)


@bp.route('/objects/<object_type>/delete', methods=['POST'])
def object_type_delete(object_type):
    try:
        obj_type = getattr(importlib.import_module('app.models'), object_type)
        object_id = int(request.form.get('id'))
    except AttributeError:
        abort(404)
    except (ValueError, TypeError):
        abort(400)
    if obj_type not in get_enumerated_objects():
        abort(400)
    try:
        obj = db.session.scalars(sa.select(obj_type).where(obj_type.id==object_id)).one()
    except exc.NoResultFound:
        abort(404)
    i, t = obj.id, obj.title
    db.session.delete(obj)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete enumerated object '{object_type}' #{i}: '{t}'")
    flash(_l("Enumerated object deleted successfully"), 'success')
    return redirect(url_for('admin.object_type_index', object_type=object_type))


@bp.route('/status/index')
def status_index():
    ''' Returns a list of all possible state objects '''
    objs = get_status_objects()
    ctx = DefaultEnvironment('status_index')()
    side_libraries.library_required('bootstrap_table')
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all status objects")
    return render_template('admin/status_index.html', objs=objs, **ctx)


@bp.route('/status/<object_type>/edit_transits', methods=['GET', 'POST'])
def status_type_transits(object_type: str):
    ''' A route for changing possible transitions between states '''
    try:
        obj_type = getattr(importlib.import_module('app.models'), object_type)
    except AttributeError:
        abort(404)
    if obj_type not in get_status_objects():
        abort(400)
    form = get_status_transit_form(obj_type, db.session)()
    form_attrs = []
    for i in form.attr_names:
        na = []
        for j in i:
            na.append(getattr(form, j))
        form_attrs.append(na)
    if form.validate_on_submit():
        form.populate_statuses()
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit status type transits")
        flash(_l("Possible transitions for the object «%(verbose_name)s» have been successfully updated", verbose_name=obj_type.Meta.verbose_name), 'success')
        return redirect(url_for('admin.status_index'))
    elif request.method == 'GET':
        form.load_exist_statuses()
    ctx = DefaultEnvironment('status_type_transits', obj_type)()
    return render_template('admin/status_type_transits.html', **ctx,
                           form=form, form_attrs=form_attrs,
                           all_objs=form.all_objs)

@bp.route('/issues/templates/index')
def issue_template_index():
    templs = db.session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.archived == False)).all()
    ctx = DefaultEnvironment('issue_template_index')()
    side_libraries.library_required('bootstrap_table')
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request all issue templates")
    return render_template('issue_templates/index.html', **ctx, templates=templs)


@bp.route('/issues/templates/new', methods=["GET", "POST"])
def issue_template_new():
    form = issue_template_forms.IssueTemplateCreateForm(db.session)
    if form.validate_on_submit():
        templ = models.IssueTemplate()
        form.populate_obj(db.session, templ, current_user)
        db.session.add(templ)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new issue template #{templ.id}: '{templ.title}'")
        flash(_l("New Issue template successfully added"), "success")
        return redirect(url_for('admin.issue_template_show', template_id=templ.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, models.IssueTemplate)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('issue_template_new')()
    context = {'form': form, "ckeditor_height": "100px"}
    return render_template('issue_templates/new.html', **ctx, **context)


@bp.route('/issues/templates/<template_id>/show')
def issue_template_show(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = get_or_404(db.session, models.IssueTemplate, template_id)
    ctx = DefaultEnvironment('issue_template_show', templ)()
    context = {'template': templ}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request issue template #{templ.id}")
    return render_template('issue_templates/show.html', **ctx, **context)


@bp.route('/issues/templates/<template_id>/edit', methods=["GET", "POST"])
def issue_template_edit(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = get_or_404(db.session, models.IssueTemplate, template_id)
    form = issue_template_forms.IssueTemplateEditForm(db.session)
    if form.validate_on_submit():
        form.populate_obj(db.session, templ)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' update issue template #{templ.id}: '{templ.title}'")
        flash(_l("Issue template successfully updated"), 'success')
        return redirect(url_for('admin.issue_template_show', template_id=templ.id))
    elif request.method == "GET":
        form.load_exist_value(templ)
    ctx = DefaultEnvironment('issue_template_edit', templ)()
    context = {'form': form, "ckeditor_height": "100px"}
    return render_template('issue_templates/new.html', **ctx, **context)


@bp.route('/issues/templates/<template_id>/delete', methods=["POST", "DELETE"])
def issue_template_delete(template_id):
    try:
        template_id = int(template_id)
    except (ValueError, TypeError):
        abort(400)
    templ = get_or_404(db.session, models.IssueTemplate, template_id)
    t = templ.title
    db.session.delete(templ)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete issue template #{template_id}: '{t}'")
    flash(_l("Issue template successfully deleted"), 'success')
    return redirect(url_for('admin.issue_template_index'))


@bp.route('/templates/object-template-list')
def object_template_list():
    ctx = DefaultEnvironment('object_template_list')()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request object template list")
    return render_template('admin/object_template_list.html', **ctx)