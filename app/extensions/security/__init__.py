from werkzeug.security import generate_password_hash as werkzeug_password_hash, check_password_hash as werkzeug_check_password_hash, gen_salt
from gostcrypto import gosthash
import functools
from flask_login import current_user
import datetime
from flask_babel import lazy_gettext as _l, LazyString
from flask import request, flash, redirect, url_for, current_app, Flask
from typing import List, Optional, Set
from app.extensions.utf8strings import UTF8strings


def generate_password_hash(password: str, method: str="streebog512", salt_length: int=16) -> str:
    """ Securely hash a password for storage. A password can be compared to a stored hash
    using :func:`check_password_hash`.

    The following methods are supported:

    -   ``streebog512``, the default. Usage in GOST 34.11-2012
    - ``scrypt`` or ``pbkdf2`` - is a hash function, that use an werkzeug.security library """
    salt = gen_salt(salt_length)
    salted_password = password + ":" + salt
    if method != 'streebog512':
        return werkzeug_password_hash(password, method, salt_length=salt_length)
    else:
        h = gosthash.new('streebog512', data=salted_password.encode()).hexdigest()
        return f'streebog512${salt}${h}'


def check_password_hash(pwhash: str, password: str) -> bool:
    ''' Securely check that the given stored password hash, previously generated using
    :func:`generate_password_hash`, matches the given password.
    
    :param pwhash: The hashed password.
    :param password: The plaintext password. '''
    try:
        method, salt, hashval = pwhash.split("$", 2)
    except ValueError:
        return False
    if method != 'streebog512':
        return werkzeug_check_password_hash(pwhash, password)
    new_hash = gosthash.new('streebog512', data=(password + ":" + salt).encode()).hexdigest()
    return hashval == new_hash


def check_user_need_change_password(callback_endpoint: str, exempt_endpoint: Set[str], exempt_bp: Set[str]):
    def decorated(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if not request.endpoint or request.endpoint in exempt_endpoint or request.blueprint in exempt_bp or current_user.is_anonymous or request.endpoint == callback_endpoint:
                return func(*args, **kwargs)
            if current_user.is_password_expired or current_user.password_expired_date < datetime.datetime.now():
                print('password_expired:', current_user.is_password_expired)
                print('date:', current_user.password_expired_date)
                flash(_l("Your password has expired or the administrator has requested to change it"), 'warning')
                return redirect(url_for(callback_endpoint, user_id=current_user.id, next=request.url))
            return func(*args, **kwargs)
        return wrapped
    return decorated


def check_password_complexity(password: str) -> List[LazyString]:
    ''' Проверяет соответствие пароля требованиям парольной политики и возвращает список найденных несоответствий '''
    errors = []
    if len(password) < current_app.config["GlobalSettings"].password_min_length:
        errors.append(_l("According to the password policy, the length must be more than %(characters)s characters", characters=current_app.config["GlobalSettings"].password_min_length))
    if current_app.config["GlobalSettings"].password_lowercase_symbol_require:
        has_lowercase = False
        for i in password:
            if i in UTF8strings.utf8_lowercase:
                has_lowercase = True
                break
        if not has_lowercase:
            errors.append(_l("According to the password policy, the password must contain at least one lowercase symbol"))
    if current_app.config["GlobalSettings"].password_uppercase_symbol_require:
        has_uppercase = False
        for i in password:
            if i in UTF8strings.utf8_uppercase:
                has_uppercase = True
                break
        if not has_uppercase:
            errors.append(_l("According to the password policy, the password must contain at least one uppercase symbol"))
    if current_app.config["GlobalSettings"].password_numbers_require:
        has_numbers = False
        for i in password:
            if i in UTF8strings.digits:
                has_numbers = True
                break
        if not has_numbers:
            errors.append(_l("According to the password policy, the password must contain at least one digit"))
    if current_app.config["GlobalSettings"].password_special_symbols_require:
        has_special_symbol = False
        for i in password:
            if i in UTF8strings.punctuation:
                has_special_symbol = True
                break
        if not has_special_symbol:
            errors.append(_l("According to the password policy, the password must contain at least one special symbol (like !, @, #, etc)"))
    return errors


class PasswordPolicyManager:
    def __init__(self, app: Optional[Flask]=None, change_password_callback: Optional[str]=None, exempt_endpoint: Set[str]=set(), exempt_bp: Set[str] = set()):
        self.change_password_callback = change_password_callback
        exempt_endpoint.add('static')
        self.exempt_endpoint = exempt_endpoint
        self.exempt_bp = exempt_bp
        if app:
            self.init_app(app)
    def init_app(self, app: Flask):
        if not self.change_password_callback:
            return None
        
        @app.before_request
        @self.need_change_password
        def check_if_need_change_password_before_request():
            return None
    
    def need_change_password(self, func):
        return check_user_need_change_password(self.change_password_callback, self.exempt_endpoint, self.exempt_bp)(func)