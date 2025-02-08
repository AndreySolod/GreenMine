from app import db, logger
from app.controllers.users import bp
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from flask import url_for, request, redirect, render_template, flash, abort, jsonify
from app.models import User, FileData
from app.helpers.general_helpers import CurrentObjectInfo, CurrentObjectAction, get_or_404
from app.helpers.users_helpers import UserSidebar
from app.helpers.main_page_helpers import DefaultEnvironment as MainPageEnvironment
from .forms import EditUserPasswordForm, UserFormCreate, UserFormEdit, LoginForm, UserFormDelete
from flask_babel import lazy_gettext as _l
from app.helpers.roles import UserHimself, has_user_role, administrator_only, only_for_roles


@bp.route('/index')
@login_required
def user_index():
    users = db.session.scalars(db.select(User)).all()
    ctx = MainPageEnvironment('User', 'index')()
    context = {'users': users, 'form_delete': UserFormDelete()}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request user list")
    return render_template('users/index.html', **context, **ctx)


@bp.route('/<int:user_id>', methods=["GET", "POST"])
@bp.route('/<int:user_id>/show', methods=["GET", "POST"])
@login_required
def user_show(user_id):
    u = db.get_or_404(User, user_id)
    if has_user_role([UserHimself], u):
        act1 = CurrentObjectAction(_l("Edit"), "fa-solid fa-user-pen", url_for('users.user_edit', user_id=u.id))
        act2 = CurrentObjectAction(_l("Change password"), "fa-solid fa-key", 'modalEditPasswordInformation', action_type='button_modal')
        act3 = CurrentObjectAction(_l("Delete"), "fa-solid fa-user-slash", url_for('users.user_delete', user_id=u.id), confirm=_l("Are you sure you want to delete this user?"), btn_class='btn-danger', method="DELETE")
        current_object = CurrentObjectInfo(_l("User #%(user_id)s: %(user_title)s", user_id=u.id, user_title=u.title), "fa-solid fa-user-tie", actions=[act1, act2, act3])
    else:
        current_object = CurrentObjectInfo(_l("User #%(user_id)s: %(user_title)s", user_id=u.id, user_title=u.title), "fa-solid fa-user-tie")
    sidebar_data = UserSidebar(u, 'user_show')()
    if has_user_role([UserHimself], u):
        change_password_form = EditUserPasswordForm()
        if change_password_form.validate_on_submit():
            u.set_password(change_password_form.password.data)
            db.session.commit()
            return redirect(url_for('users.user_show', user_id=u.id))
    else:
        change_password_form = None
    context = {'user': u, 'title': _l("User «%(title)s»", title=u.title), 'current_object': current_object,
               'sidebar_data': sidebar_data, 'password_form': change_password_form}
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' request user info for user #{user_id}")
    return render_template('users/show.html', **context)


@bp.route('/new', methods=["GET", "POST"])
@login_required
@administrator_only
def user_new():
    form = UserFormCreate()
    ctx = MainPageEnvironment('User', 'new')()
    if form.validate_on_submit():
        u = User()
        db.session.add(u)
        form.populate_obj(db.session, u, current_user)
        u.set_password(form.password.data)
        if form.avatar.data:
            avatar = FileData()
            filename = secure_filename(form.avatar.data.filename)
            avatar.title = filename
            avatar.extension = filename.split(".")[-1]
            avatar.description = str(_l("Avatar for %(login)s", login=form.login.data))
            avatar.data = request.files[form.avatar.name].read()
            u.avatar = avatar
            db.session.add(avatar)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' successfully created a new user #{u.id}")
        flash(_l("User «%(title)s» successfully created", title=u.title), 'success')
        return redirect(url_for('users.user_show', user_id=u.id))
    elif request.method == 'GET':
        form.load_default_data(db.session, User)
        form.load_data_from_json(request.args)
    return render_template('users/new.html', form=form, **ctx)


@bp.route('/<int:user_id>/edit', methods=["GET", "POST"])
@login_required
def user_edit(user_id):
    user = get_or_404(db.session, User, user_id)
    if not has_user_role([UserHimself], user):
        abort(403)
    form = UserFormEdit()
    sidebar_data = UserSidebar(user, 'user_edit')()
    current_object = CurrentObjectInfo(_l("Edit user #%(user_id)s", user_id=user.id), "fa-solid fa-user-pen")
    if form.validate_on_submit():
        form.populate_obj(db.session, user)
        if form.avatar.data:
            if user.avatar is not None:
                db.session.delete(user.avatar)
            avatar = FileData()
            filename = secure_filename(form.avatar.data.filename)
            avatar.title = filename
            avatar.extension = filename.split(".")[-1]
            avatar.description = str(_l("Avatar for %(login)s", login=user.login))
            avatar.data = request.files[form.avatar.name].read()
            user.avatar = avatar
            db.session.add(avatar)
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' edit user #{user.id}")
        flash(_l("User «%(title)s» successfully changed", title=user.title), 'success')
        db.session.commit()
        return redirect(url_for('users.user_show', user_id=user.id))
    elif request.method == "GET":
        form.load_exist_value(user)
        form.load_data_from_json(request.args)
    context = {'form': form, 'title': _l('Edit user #%(user_id)s', user_id=user.id),
               'sidebar_data': sidebar_data, 'current_object': current_object}
    return render_template('users/edit.html', **context)


@bp.route('/delete', methods=["POST"])
@login_required
def user_delete():
    fd = UserFormDelete()
    if fd.validate_on_submit():
        is_current_user = current_user.id == int(fd.user_id.data)
        user = get_or_404(db.session, User, int(fd.user_id.data))
        if not has_user_role([UserHimself], user):
            abort(403)
        uid = user.id
        db.session.delete(user)
        db.session.commit()
        logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' delete user #{user.id}")
        flash(_l("User #%(uid)s: «%(title)s» sucessfully deleted", uid=uid, title=user.title), 'success')
        if is_current_user:
            logout_user()
        return redirect(url_for('users.user_index'))
    abort(400)


@bp.route('/login', methods=["GET", "POST"])
def user_login():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('users.user_show', user_id=current_user.id))
    if form.validate_on_submit():
        user = db.session.scalars(db.select(User).where(User.login==form.login.data)).first()
        if user is None or not user.check_password(form.password.data):
            flash(_l("Invalid user login or password"), 'danger')
            logger.warning(f"User '{getattr(user, 'login', 'Anonymous')}' trying to login with wrong password")
            return redirect(url_for('users.user_login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('users.user_show', user_id=user.id)
        logger.info(f"User '{getattr(user, 'login', 'Anonymous')}' entered the system")
        return redirect(next_page)
    else:
        context = {"form": form,
                   'title': _l("Enter"), 'need_main_style': False,
                   'flash_in_header': True}
        return render_template('users/login.html', **context)


@bp.route('/logout')
@login_required
def user_logout():
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' was logged out from system")
    logout_user()
    return redirect(url_for('users.user_login'))
