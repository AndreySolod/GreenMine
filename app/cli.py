from app import db
from flask import current_app
import os
import shutil
import yaml
import importlib
from sqlalchemy.inspection import inspect
from sqlalchemy import func, exc
from flask_migrate import init, migrate, upgrade
import logging
import click
import sqlalchemy.orm.collections as sacollections


def register(app):
    @app.cli.group()
    def greenmine_command():
        ''' Группа для загрузки каких-либо инициирующих данных '''
        pass

    def get_base_data(e, data):
        # Вносит простые данные - т.е. те, которые не являются отношениями (строки, числа, логические значения и т.д.)
        base_data = inspect(e.__class__).column_attrs.keys() # Это все простые значения
        for attr_name, attr_value in data.items():
            if attr_name in base_data:
                # Если атрибут - простой
                setattr(e, attr_name, attr_value)
            elif attr_name.startswith('_function__'):
                # Если начинается с _function__, то необходимо интерпретировать как вызов метода на данном значении. Например, для установки хэша пароля для пользователя
                getattr(e, attr_name[11::])(attr_value)
        return e

    def get_complex_data(e, data):
        # Вносит сложные данные - т.е. те, которые являются отношениями
        not_base_data = inspect(e.__class__).relationships.keys() # Все отношения
        for attr_name, attr_value in data.items():
            if attr_name in not_base_data:
                if not isinstance(attr_value, list):
                    # Это простое отношение - т.е. это не связь "Многие ко многим"
                    attr_class = inspect(e.__class__).relationships[attr_name].entity.class_  # Получили класс, на который ссылается сложный объект
                    #  Теперь ищем такой объект в переданном списке
                    linked_element = db.session.scalars(db.select(attr_class).where(attr_class.string_slug==attr_value)).first()
                    if linked_element is None:
                        # Такого объекта не нашли - возвращаем ошибку.
                        app.logger.error(f"attr_class = {attr_class}; attr_value = {attr_value}")
                        app.logger.error("Объекта {} с таким строковым идентификатором у атрибута {} не существует: {}".format(attr_class.__name__, attr_name, attr_value))
                        raise KeyError("Объекта {} с таким строковым идентификатором у атрибута {} не существует: {}".format(attr_class.__name__, attr_name, attr_value))
                    # Теперь устанавливаем этот атрибут в объект
                    setattr(e, attr_name, linked_element)
                else:
                    # Здесь связь "Многие ко многим"
                    for attr_value_element in attr_value:
                        attr_class = inspect(e.__class__).relationships[attr_name].entity.class_
                        linked_element = db.session.scalars(db.select(attr_class).where(attr_class.string_slug == attr_value_element)).first()
                        if linked_element is None:
                            app.logger.error(f"attr_class = {attr_class}; attr_value_element = {attr_value_element}")
                            app.logger.error("Объекта {} с таким строковым идентификатором у атрибута {} не существует: {}".format(attr_class.__name__, attr_name, attr_value_element))
                            raise KeyError("Объекта {} с таким строковым идентификатором у атрибута {} не существует: {}".format(attr_class.__name__, attr_name, attr_value_element))
                        now_attr = getattr(e, attr_name)
                        if isinstance(now_attr, sacollections.InstrumentedSet):
                            now_attr.add(linked_element)
                        else:
                            now_attr.append(linked_element)
                        setattr(e, attr_name, now_attr)
        return e
    
    def load_simple_data_to_database(classes: str, object_classes: dict, module, module_obj_list: dict):
        ''' Создаёт в БД класс classes и заносит в него объекты из object_classes, представленные в виде dict(import from yaml) формате. При этом заносятся только "простые" данные,
         т. е. такие данные, которые не представляют из себя отношения '''
        module = importlib.import_module('app.models') # Imported module, where attribute is model to change
        if len(object_classes) == 1 and list(object_classes[0].keys())[0] == '_import_module':
            # Processing of external import modules
            app.logger.info(f'Start import simple data for module "{object_classes}"')
            e = getattr(module, classes)
            import_default_data_name = list(object_classes[0].values())[0]
            import_class = importlib.import_module('default_database_value.modules.' + import_default_data_name).ImportDefaultData()
            import_class.data(app, e, db)
            module_obj_list[classes] = import_class
            return None
        for elem in object_classes:
            e = getattr(module, classes)()
            e.string_slug = list(elem.keys())[0]
            for attr in elem.values():
                e = get_base_data(e, attr)
                db.session.add(e)
                db.session.commit()
    

    def load_complex_data_to_database(classes: str, object_classes: dict, module, module_obj_list:dict):
        ''' Complements the elements in the database of the "classes" class through attribute in "object_classes", presented in the form of dict (import from yaml). In this case, only relationships is entered. '''
        if (len(object_classes) == 1 and list(object_classes[0].keys())[0] == '_import_module'):
            # Processing of external import modules - complex data
            nic = module_obj_list[classes]
            if not nic.is_complex:
                return None
            else:
                app.logger.info(f'Start import complex data for module "{object_classes}"')
                nic.complex_data(app, db, module)
                return None
        for elem in object_classes:
            cls = getattr(module, classes)
            e = db.session.scalars(db.select(cls).where(cls.string_slug==list(elem.keys())[0])).first()
            for attrs in elem.values():
                get_complex_data(e, attrs)
                db.session.add(e)
                db.session.commit()


    def _load_default_database():
        root = os.path.join(os.path.dirname(app.root_path), 'default_database_value') # Migration root
        init_db_val_file = os.path.join(root, 'initial_database_value.yml')
        module = importlib.import_module('app.models')
        with open(init_db_val_file, 'r') as f:
            # Read file in .yml format
            read_data = yaml.load(f, Loader=yaml.FullLoader)
        module_obj_list = {} # Dict of imports module, where keys - class names, values - import module object
        for classes, object_classes in read_data.items():
            # Simple data processing
            try:
                load_simple_data_to_database(classes, object_classes, module, module_obj_list)
            except exc.IntegrityError:
                app.logger.error("Something went wrong. Try run 'flask db migrate && flask db upgrade' and recall this command")
                return None
        for classes, object_classes in read_data.items():
            # Complex data processing
            try:
                load_complex_data_to_database(classes, object_classes, module, module_obj_list)
            except exc.IntegrityError as err:
                app.logger.error("IntegrityError:")
                app.logger.error(str(err))
                app.logger.error("Something went wrong. Try run 'flask db migrate && flask db upgrade' and recall this command")
                return None


    @greenmine_command.command()
    def load_default_database():
        ''' Load data from file initial_database_value.yml to clear database '''
        _load_default_database()


    def _db_init():
        ''' Created new database and configured migrations '''
        init()
        app.logger.info('start rewriting mako file')
        mako_file = os.path.join(os.path.dirname(app.root_path), app.extensions['migrate'].directory, 'script.py.mako')
        with open(mako_file, 'r') as f:
            mako_data = f.read().split('\n')
        with open(mako_file, 'w') as f:
            f.write('\n'.join(mako_data[:9:] + ['import app'] + mako_data[9::]))
        app.logger.info("rewriting ends")


    @greenmine_command.command()
    def reset_database():
        ''' Dropped existed database and created new with drop 'migrations' folder '''
        db.reflect()
        db.drop_all()
        root = os.path.dirname(app.root_path)
        try:
            shutil.rmtree(os.path.join(root, "migrations"))
        except FileNotFoundError:
            app.logger.warning('All migrations have already been deleted')
        _db_init()
        migrate(message='Initial migrate')
        upgrade()
        app.logger.info('Starting load default value for database table')
        _load_default_database()
        app.logger.info('Load ends')


    @greenmine_command.command()
    def db_init():
        _db_init()
    
    @greenmine_command.command()
    def update_database_value():
        ''' Filled empty tables in database with values from the file initial_database_value '''
        root = os.path.join(os.path.dirname(app.root_path), 'default_database_value') # Migration root
        init_db_val_file = os.path.join(root, 'initial_database_value.yml')
        module = importlib.import_module('app.models')
        with open(init_db_val_file, 'r') as f:
            # Read file in .yml format
            app.logger.info("Reading default database file")
            read_data = yaml.load(f, Loader=yaml.FullLoader)
        module_obj_list = {} # Dict of imports module, where keys - class names, values - import module object
        app.logger.info("Starting importing data to empty tables")
        emptys_tables = []
        for classes, object_classes in read_data.items():
            # Processing simple data
            now_object = getattr(module, classes)
            try:
                count_obj = db.session.execute(db.select(func.count()).select_from(now_object)).one()[0]
            except (exc.IntegrityError) as e:
                app.logger.error(str(e))
                app.logger.error("Something going wrong. Try run 'flask db migrate && flask db upgrade'")
                return None
            if count_obj == 0:
                app.logger.info(f"Importing simple data for table of class {classes}")
                emptys_tables.append(now_object)
                load_simple_data_to_database(classes, object_classes, module, module_obj_list)
        
        for now_object in emptys_tables:
            app.logger.info(f"Importing complex data for table of class {now_object}")
            object_classes = read_data[now_object.__name__]
            load_complex_data_to_database(now_object.__name__, object_classes, module, module_obj_list)
    
    @greenmine_command.command()
    @click.option('--table', help="Table to recreate")
    def recreate_table(table):
        ''' Dropped the specified table and creates it again, filled it from the files initial_database_value.yml '''
        root = os.path.join(os.path.dirname(app.root_path), 'default_database_value') # Migration root - where initial script and values are stored
        init_db_val_file = os.path.join(root, 'initial_database_value.yml')
        module = importlib.import_module('app.models')
        with open(init_db_val_file, 'r') as f:
            # Read file in format .yml
            app.logger.info("Reading default database file")
            read_data = yaml.load(f, Loader=yaml.FullLoader)
        module_obj_list = {} # Dict of imports module, where keys - class names, values - import module object
        try:
            now_object = getattr(module, table)
        except AttributeError:
            app.logger.error(f"Import error: no such model in project: {table}")
            return None
        try:
            object_classes = read_data[table]
        except KeyError:
            app.logger.error(f"Import error: no such table in default_database_value: {table}")
            return None
        app.logger.info("Dropped old tables")
        now_object.__table__.drop(db.engine, checkfirst=True)
        app.logger.info('Creating new table')
        now_object.__table__.create(db.engine)
        app.logger.info('Table create successfully')
        db.session.commit()
        app.logger.info("Old table dropped. Added new value to database")
        load_simple_data_to_database(table, object_classes, module, module_obj_list)
        app.logger.info('Now load complex data to database')
        load_complex_data_to_database(table, object_classes, module, module_obj_list)
        app.logger.info('Load ends.')
    
    @app.cli.group()
    def translate():
        ''' Translation and localization command '''
        pass

    @translate.command()
    def update():
        """Update all languages."""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system('pybabel update -i messages.pot -d app/translations'):
            raise RuntimeError('update command failed')
        os.remove('messages.pot')

    @translate.command()
    @click.option('-f', is_flag=True, show_default=True, default=False, help="Forced to compile language (include fuzzy translates)")
    def compile(f):
        """Compile all languages."""
        if f:
            if os.system('pybabel compile -f -d app/translations'):
                raise RuntimeError('compile command failed')
        else:
            if os.system('pybabel compile -d app/translations'):
                raise RuntimeError('compile command failed')