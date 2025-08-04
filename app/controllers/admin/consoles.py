from app.controllers.admin import bp
from app import db, side_libraries, socketio, logger, sanitizer
from app.helpers.admin_helpers import DefaultEnvironment
from app.helpers.general_helpers import authenticated_only
from flask import url_for, redirect, render_template, flash
from flask_login import current_user
import app.models as models
import sqlalchemy as sa
from contextlib import redirect_stdout, redirect_stderr
import io
import traceback


@bp.route('/console')
def console():
    ctx = DefaultEnvironment()()
    side_libraries.library_required('ace')
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' opened console")
    return render_template('admin/console.html', **ctx)


@socketio.on("console command", namespace="/admin")
@authenticated_only
def console_command(message):
    """
    Handles console command execution over WebSocket for administrators.

    This function is triggered when a 'console command' event is received. It checks if the current user has administrator privileges,
    logs the command execution attempt, and executes the provided Python code in a restricted context. The output (or error) is
    captured, sanitized, and returned in a format suitable for HTML display.

    Args:
        message (str): The Python code to be executed.

    Returns:
        str: The sanitized output of the command execution, with newlines replaced by HTML line breaks. Returns None if the user
            is not an administrator.
    """
    if not current_user.position.is_administrator:
        logger.warning(f"User '{getattr(current_user, 'login', 'Anonymous')}' tried to execute console command as non-administrator")
        return None
    logger.info(f"User '{getattr(current_user, 'login', 'Anonymous')}' executed console command: {message}")
    
    context = {
        "models": models, "db":db, "sa": sa
    }
    output_command_result = io.StringIO()
    try:
        with redirect_stdout(output_command_result), redirect_stderr(output_command_result):
            exec(message, context)
    except Exception as e:
        output_command_result.write("Exception: " + e.__class__.__name__ + ": "+ str(e))
    return sanitizer.escape(output_command_result.getvalue()).replace('\n', '<br>')