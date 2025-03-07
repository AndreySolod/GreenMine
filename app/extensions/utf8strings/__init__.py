import string

class UTF8strings:
    ''' Класс, предназначенный для хранения всех UTF8-символов (включая ascii и русский алфавит) '''
    ascii_uppercase = string.ascii_uppercase
    ascii_lowercase = string.ascii_lowercase
    digits = string.digits
    ascii_letters = string.ascii_letters
    hexdigits = string.hexdigits
    whitespace = string.whitespace
    punctuation = string.punctuation
    octdigits = string.octdigits
    printable = string.printable
    utf8_uppercase = string.ascii_uppercase + "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    utf8_lowercase = string.ascii_lowercase + "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
