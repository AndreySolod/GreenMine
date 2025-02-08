from werkzeug.security import generate_password_hash as werkzeug_password_hash, check_password_hash as werkzeug_check_password_hash, gen_salt
from gostcrypto import gosthash


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