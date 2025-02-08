from app import db, logger, side_libraries
from app.controllers.wiki_pages import bp
from flask_login import login_required, current_user
from flask import request, render_template, url_for, redirect, flash, abort, jsonify
from app.models import WikiPage, WikiDirectory
from app.helpers.general_helpers import get_or_404
from app.helpers.main_page_helpers import DefaultEnvironment
import sqlalchemy
import sqlalchemy.exc as exc
from .forms import WikiDirectoryNewForm, WikiPageNewForm, WikiPageEditForm
from flask_babel import lazy_gettext as _l


@bp.route('/wikidirectory/index')
@login_required
def pagedirectory_index():
    directories = db.session.scalars(db.select(WikiDirectory).where(WikiDirectory.parent_directory_id == None)).all()
    pages = db.session.scalars(db.select(WikiPage).where(WikiPage.directory_id == None)).all()
    ctx = DefaultEnvironment('WikiPage', 'index')()
    context = {'directories': directories, 'pages': pages}
    side_libraries.library_required('contextmenu')
    return render_template('wiki_pages/index.html', **context, **ctx)


@bp.route('/wikidirectory/ajax-new', methods=["POST"])
@login_required
def pagedirectory_ajax_new():
    dir_title = request.form.get('title') or ''
    dir_description = request.form.get('description') or ''
    try:
        parent_dir_id = request.form.get('parent_dir_id')
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to create wiki directory with non-integer parent_dir_id {request.form.get('parent_dir_id')}")
        abort(404)
    try:
        db.session.execute(db.select(WikiDirectory.id).where(WikiDirectory.id == parent_dir_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    wd = WikiDirectory(title=dir_title, description=dir_description, parent_directory_id=parent_dir_id, created_by_id=current_user.id)
    db.session.add(wd)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new wiki directory #{wd.id}")
    return jsonify({'status': 'success', 'id': wd.id})


@bp.route('/wikidirectory/new', methods=['GET', 'POST'])
@login_required
def pagedirectory_new():
    form = WikiDirectoryNewForm(db.session)
    if form.validate_on_submit():
        directory = WikiDirectory()
        form.populate_obj(db.session, directory, current_user)
        db.session.add(directory)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new wiki directory #{directory.id}")
        flash(_l("The Wiki page directory «%(title)s» has been successfully created", title=directory.title), "success")
        return redirect(url_for('wiki_pages.pagedirectory_index'))
    elif request.method == "GET":
        form.load_default_data(db.session, WikiDirectory)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('WikiDirectory', 'new_dir')()
    return render_template('wiki_pages/wikidirectory_new.html', **ctx, form=form)


@bp.route('/wikidirectory/<wikidirectory_id>/edit', methods=["POST"])
@login_required
def pagedirectory_edit(wikidirectory_id):
    try:
        wikidirectory_id = int(wikidirectory_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to edit wiki directory with non-integer wikidirectory_id {wikidirectory_id}")
        abort(404)
    title = request.form.get('title')
    description = request.form.get('description')
    try:
        directory = db.session.scalars(db.select(WikiDirectory).where(WikiDirectory.id==wikidirectory_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    directory.title = title
    directory.description = description
    directory.updated_by_id = current_user.id
    db.session.add(directory)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit wiki directory #{directory.id}")
    return jsonify({'status': 'success'})


@bp.route('/wikidirectory/<wikidirectory_id>/delete', methods=["POST"])
@login_required
def pagedirectory_delete(wikidirectory_id):
    try:
        directory_id = int(wikidirectory_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to delete wiki directory with non-integer wikidirectory_id {wikidirectory_id}")
        abort(404)
    try:
        wd = db.session.scalars(db.select(WikiDirectory).where(WikiDirectory.id == directory_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    db.session.delete(wd)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete wiki directory #{wikidirectory_id}")
    return jsonify({'status': 'success'})


@bp.route('/wikipage/<wikipage_id>/show')
@login_required
def wikipage_show(wikipage_id):
    try:
        wikipage_id = int(wikipage_id)
    except (ValueError, TypeError):
        abort(404)
    try:
        page = db.session.scalars(db.select(WikiPage).where(WikiPage.id == wikipage_id)).one()
    except (exc.MultipleResultFound, exc.NoResultFound):
        abort(404)
    ctx = DefaultEnvironment('WikiPage', 'show', obj_val=page)()
    return render_template('wiki_pages/wikipage_show.html', **ctx, page=page)


@bp.route('/wikipage/new', methods=["GET", "POST"])
@login_required
def wikipage_new():
    form = WikiPageNewForm(db.session)
    if form.validate_on_submit():
        wp = WikiPage()
        form.populate_obj(db.session, wp, current_user)
        db.session.add(wp)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new wiki page")
        flash(_l('The page has been created successfully'), 'success')
        return redirect(url_for('wiki_pages.wikipage_show', wikipage_id=wp.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, WikiPage)
        form.load_data_from_json(request.args)
    ctx = DefaultEnvironment('WikiPage', 'new')()
    return render_template('wiki_pages/wikipage_new.html', **ctx, form=form)


@bp.route('/wikipage/ajax-new', methods=["POST"])
@login_required
def wikipage_ajax_new():
    parent_dir_id = request.form.get('parent_dir_id') or ''
    try:
        parent_dir_id = int(parent_dir_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to create wiki page with non-integer parent_dir_id {request.form.get('parent_dir_id')}")
        abort(404)
    pd = get_or_404(db.session, WikiDirectory, parent_dir_id)
    wp = WikiPage(title='', description='', text='', created_by_id=current_user.id, directory_id=parent_dir_id)
    db.session.add(wp)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' create new wiki page")
    return jsonify({'status': 'success', 'page_id': wp.id})


@bp.route('/wikipage/<wikipage_id>/edit', methods=["GET", "POST"])
@login_required
def wikipage_edit(wikipage_id):
    try:
        wikipage_id = int(wikipage_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to edit wiki page with non-integer wikipage_id {wikipage_id}")
        abort(404)
    try:
        wp = db.session.scalars(db.select(WikiPage).where(WikiPage.id == wikipage_id)).one()
    except (exc.MultipleResultsFound, exc.NoResultFound):
        abort(404)
    form = WikiPageEditForm(db.session)
    if form.validate_on_submit():
        form.populate_obj(db.session, wp)
        db.session.add(wp)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit wiki page #{wp.id}")
        flash(_l('The page has been changed successfully'), 'success')
        return redirect(url_for('wiki_pages.wikipage_show', wikipage_id=wp.id))
    elif request.method == 'GET':
        form.load_exist_value(wp)
    ctx = DefaultEnvironment('WikiPage', 'edit')()
    return render_template('wiki_pages/wikipage_new.html', **ctx, form=form)


@bp.route('/wikipage/ajax-edit', methods=["POST"])
@login_required
def wikipage_ajax_edit():
    title = request.form.get('title') or ''
    description = request.form.get('description') or ''
    page_id = request.form.get('page_id') or ''
    try:
        page_id = int(page_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to edit wiki page with non-integer wikipage_id {page_id}")
        abort(404)
    page = get_or_404(db.session, WikiPage, page_id)
    page.title = title
    page.description = description
    page.updated_by_id = current_user.id
    db.session.add(page)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit wiki page #{page.id}")
    return jsonify({'status': 'success'})


@bp.route('/wikipage/ajax-delete', methods=["POST"])
@login_required
def wikipage_ajax_delete():
    page_id = request.form.get('page_id') or None
    try:
        page_id = int(page_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to delete wiki page with non-integer wikipage_id {page_id}")
        abort(404)
    page = get_or_404(db.session, WikiPage, page_id)
    db.session.delete(page)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete wiki page #{page.id}")
    return jsonify({'status': 'success'})


@bp.route('/wikipage/<wikipage_id>/delete', methods=["POST", "DELETE"])
@login_required
def wikipage_delete(wikipage_id):
    try:
        wikipage_id = int(wikipage_id)
    except (ValueError, TypeError):
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' trying to delete wiki page with non-integer wikipage_id {wikipage_id}")
        abort(404)
    page = get_or_404(db.session, WikiPage, wikipage_id)
    db.session.delete(page)
    db.session.commit()
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete wiki page #{page.id}")
    flash(_l('The page has been deleted successfully'), 'success')
    return redirect(url_for('wiki_pages.pagedirectory_index'))


@bp.route('/tree-wikistruct')
@login_required
def wiki_ajax_struct():
    if 'id' not in request.args or request.args['id'] == '#':
        dir_id = None
    else:
        try:
            dir_id = int(request.args.get('id'))
        except (TypeError, ValueError):
            abort(404)
    all_dirs = db.session.scalars(db.select(WikiDirectory).where(WikiDirectory.parent_directory_id == dir_id)).all()
    r = []
    for d in all_dirs:
        if d.subdirectories or d.pages:
            r.append({'id': d.id, 'text': d.title, 'icon': 'fa-solid fa-folder', 'children': True})
        else:
            r.append({'id': d.id, 'text': d.title, 'icon': 'fa-solid fa-folder'})
    all_files = db.session.scalars(db.select(WikiPage).where(WikiPage.directory_id == dir_id))
    for f in all_files:
        r.append({'text': f.title, 'icon': 'fa-solid fa-file', 'a_attr': {'href': url_for('wiki_pages.wikipage_show', wikipage_id=f.id)}})
    return jsonify(r)