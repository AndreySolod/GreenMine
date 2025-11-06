from app import sanitizer, db
from app.controllers.forms import FlaskForm, Select2MultipleField, Select2Field
from flask import request, url_for, g
import wtforms
from wtforms import validators
from flask_wtf.file import FileAllowed
from app.helpers.projects_helpers import validate_host, validate_service
from app.action_modules.classes import ActionModule
import app.models as models
import sqlalchemy as sa
import sqlalchemy.exc as exc
import sqlalchemy.orm as so
import re
import binascii
from typing import List, Dict
from flask_babel import lazy_gettext as _l


def set_credential_data(cred: models.Credential, element: Dict[str, str], project_id: int, session: so.Session) -> None:
    if 'password' in element:
        cred.password = sanitizer.escape(element['password'])
    if 'password_hash' in element:
        cred.password_hash = sanitizer.escape(element['password_hash'])
    if 'description' in element:
        if cred.description:
            cred.description += '<p>' + sanitizer.escape(element['description']) + '</p>'
        else:
            cred.description = '<p>' + sanitizer.escape(element['description']) + '</p>'
    if 'received_from' in element:
        rfi = session.scalars(sa.select(models.Host).where(models.Host.id.in_(list(map(int, element['received_from']))))).all()
        cred.received_from.update(set(rfi))
    if 'hash_type' in element:
        cred.hash_type = db.session.scalars(sa.select(models.HashType).where(models.HashType.id == int(element['hash_type']))).first()
    if 'check_wordlist' in element:
        cred.check_wordlist_id = int(element['check_wordlist'])
    if 'services' in element:
        svc = session.scalars(sa.select(models.Service).where(models.Service.id.in_(list(map(int, element['services']))))).all()
        cred.services.update(svc)
    session.add(cred)
    session.commit()


def process_credentials_multiple_import_data(project_id: int, processed_data: List[Dict[str, str]], created_by_id: int, session:so.Session) -> None:
    for e in processed_data:
        cred = None
        if 'login' in e and 'password_hash' in e and 'password' in e:
            try:
                cred = session.scalars(sa.select(models.Credential).where(sa.and_(models.Credential.login==e['login'],
                                                                                    models.Credential.password==e['password'],
                                                                                    models.Credential.password_hash==e['password_hash'],
                                                                                    models.Credential.project_id==project_id))).one()
            except exc.MultipleResultsFound:
                continue
            except exc.NoResultFound:
                cred = session.scalars(sa.select(models.Credential).where(sa.and_(models.Credential.login == e["login"].strip(),
                                                                                  models.Credential.password_hash==e["password_hash"].strip(),
                                                                                  models.Credential.project_id==project_id))).first()
        elif 'login' in e and 'password_hash' in e:
            try:
                cred = session.scalars(sa.select(models.Credential).where(sa.and_(models.Credential.login==e['login'],
                                                                                    models.Credential.password_hash==e['password_hash'],
                                                                                    models.Credential.project_id==project_id))).one()
            except exc.MultipleResultsFound:
                # If we find this credential - add to any credential  comprometed source and check wordlist
                for i in session.scalars(sa.select(models.Credential).where(sa.and_(models.Credential.login==e['login'],
                                                                                    models.Credential.password_hash==e['password_hash'],
                                                                                    models.Credential.project_id==project_id))).all():
                    i.received_from.update(session.scalars(sa.select(models.Host).where(models.Host.id.in_(list(map(int, e['received_from']))))).all())
                    i.services.update(session.scalars(sa.select(models.Service).where(models.Service.id.in_(list(map(int, e['services']))))).all())
            except exc.NoResultFound:
                pass
        elif 'login' in e and 'password' in e:
            try:
                cred = session.scalars(sa.select(models.Credential).where(sa.and_(models.Credential.login==e['login'],
                                                                                    models.Credential.password==e['password'],
                                                                                    models.Credential.project_id==project_id))).one()
            except exc.MultipleResultsFound:
                continue
            except exc.NoResultFound:
                pass
        elif 'password_hash' in e:
            cred = session.scalars(sa.select(models.Credential).where(sa.and_(models.Credential.password_hash == e['password_hash'],
                                                                                models.Credential.project_id==project_id))).all()
            for c in cred:
                set_credential_data(c, e, project_id, session)
        if cred is None:
            e.setdefault('login', '-')
            cred = models.Credential(login=sanitizer.escape(e['login']), created_by_id=created_by_id, project_id=project_id)
        if not isinstance(cred, list):
            set_credential_data(cred, e, project_id, session)
    session.commit()
            


def exploit(filled_form: dict, running_user_id: int, default_options: dict, locale: str, project_id: int):
    process_credentials_multiple_import_data(project_id, filled_form['processed_credentials_data'], running_user_id, session=db.session)


class CredentialMultipleAddForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super(CredentialMultipleAddForm, self).__init__(*args, **kwargs)
        self.static_check_wordlist.choices = [('0', '---')] + [(i[0], i[1]) for i in db.session.execute(sa.select(models.CheckWordlist.id, models.CheckWordlist.title))]
        self.static_services.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).select_from(models.Project).join(models.Project.networks).join(models.Network.to_hosts).join(models.Host.services).where(models.Project.id==project_id))]
        self.static_services.callback = url_for('networks.get_select2_service_data', project_id=project_id)
        self.static_services.locale = g.locale
        self.static_services.validate_funcs = lambda x: validate_service(project_id, x)
        self.static_received_from.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Host).join(models.Host.from_network).where(models.Network.project_id == project_id))]
        self.static_received_from.callback = url_for('networks.get_select2_host_data', project_id=project_id)
        self.static_received_from.locale = g.locale
        self.static_received_from.validate_funcs = lambda x: validate_host(project_id, x)

    login_position = wtforms.IntegerField(_l("Login column number:"), validators=[validators.Optional()])
    password_hash_position = wtforms.IntegerField(_l("Password hash column number:"), validators=[validators.Optional()])
    description_position = wtforms.IntegerField(_l("Credential description column number:"), description=_l("If credential is exists, the value of this field will be added to the end of the current one."), validators=[validators.Optional()])
    password_position = wtforms.IntegerField(_l("Password column number:"), validators=[validators.Optional()])
    delimiter = wtforms.StringField(_l("Column delimither:"), default=":", validators=[validators.Optional()], description=_l("The symbol by which the rows will be divided into columns"))
    static_login = wtforms.StringField(_l("Static login:"), description=_l("The login that will match all the lines"))
    static_password_hash = wtforms.StringField(_l("Static password hash:"), validators=[validators.Optional()], description=_l("The password that will match all the lines"))
    static_hash_type = Select2Field(models.HashType, label=_l("Static hash type:"), description=_l("An hash type, that will be added to all the lines"), validators=[validators.Optional()])
    static_check_wordlist = wtforms.SelectField(_l("Static check wordlist:"), validators=[validators.Optional()])
    static_description = wtforms.StringField(_l("Static description:"), validators=[validators.Optional()], description=_l("An description string, that will be added to all credentials"))
    static_password = wtforms.StringField(_l("Static password:"), validators=[validators.Optional()], description=_l("The password that will match all the lines"))
    static_received_from = Select2MultipleField(models.Host, label=_l("%(field_name)s:", field_name=models.Credential.received_from.info["label"]), description=models.Credential.received_from.info["help_text"], validators=[validators.Optional()], attr_title="treeselecttitle")
    static_services = Select2MultipleField(models.Service, label=_l("%(field_name)s:", field_name=models.Credential.services.info["label"]), validators=[validators.Optional()], attr_title='treeselecttitle')
    content_data = wtforms.TextAreaField(_l("Content:"), description=_l("Input content to add here (one credential per line with attribute, separated by column delimither)"))
    file_data = wtforms.FileField(_l("File:"), description=_l("A file with credentials to add (one credential per line, separated by column delimither)"), validators=[FileAllowed(set(["txt"]), message=_l("Only .txt file are allowed!")), validators.Optional()])
    submit = wtforms.SubmitField(_l("Add"))

    def validate_content_data(form, field):
        if not form.file_data.data.filename and not field.data:
            raise validators.ValidationError(_l("At least one of the two fields is required: 'Content' or 'File'!"))
    
    def validate_file_data(form, field):
        if not form.content_data.data and not field.data.filename:
            raise validators.ValidationError(_l("At least one of the two fields is required: 'Content' or 'File'!"))
        
    def validate_delimiter(form, field): # maybe hide, because this will be an celery task
        if (form.file_data.data.filename != '' or form.content_data.data.strip() != ''):
            if not form.parse_result(field.data):
                raise validators.ValidationError(_l("Incorrect input delimiter - not enough columns to parse"))
        else:
            raise validators.ValidationError(_l("Incorrect input delimiter - not enough columns to parse"))
    
    def parse_result(self, delimiter: str) -> bool:
        if self.content_data.data:
            parse_data = self.content_data.data
        elif self.file_data.data:
            try:
                parse_data = request.files.get(self.file_data.name).read().decode('utf8')
            except Exception as e:
                return False
        parse_attrs = {}
        if self.login_position.data is not None:
            parse_attrs['login'] = self.login_position.data
        if self.password_hash_position.data is not None:
            parse_attrs['password_hash'] = self.password_hash_position.data
        if self.description_position.data is not None:
            parse_attrs['description'] = self.description_position.data
        if self.password_position.data is not None:
            parse_attrs['password'] = self.password_position.data
        processed_data = []
        for line in parse_data.strip().split("\n"):
            if line == '':
                continue
            line = line.split(delimiter)
            current_elem = {}
            for key, value in parse_attrs.items(): # Process static parameters (such as login, password_hash, description, etc.)
                if key == 'login' and self.static_login.data:
                    current_elem[key] = self.static_login.data.strip()
                elif key == 'password_hash' and self.static_password_hash.data:
                    current_elem[key] = self.static_password_hash.data.strip()
                elif key == 'description' and self.static_description.data:
                    current_elem[key] = self.static_description.data.strip()
                elif key == 'password' and self.static_password.data:
                    current_elem[key] = self.static_password.data.strip()
                else: # It's normal -i.e. not static data. trying to get it from sources
                    try:
                        line_data = line[value]
                        hashcat_match = re.match(r'\$HEX\[([0-9a-fA-F]+)\]', line_data) # Convert from hashcat $HEX[] to normal string
                        if hashcat_match:
                            line_data = binascii.unhexlify(hashcat_match.groups()[0]).decode('utf8')
                        current_elem[key] = line_data.strip()
                    except IndexError:
                        return False
            if len(current_elem) == 0:
                return False
            if self.static_hash_type.data:
                current_elem['hash_type'] = self.static_hash_type.data
            if self.static_check_wordlist.data:
                current_elem['check_wordlist'] = self.static_check_wordlist.data
            if self.static_services.data:
                current_elem['services'] = self.static_services.data
            if self.static_received_from.data:
                current_elem['received_from'] = self.static_received_from.data
            processed_data.append(current_elem)
        self.additional_form_attrs = {'processed_credentials_data': processed_data}
        return True


class MultipleImportCredentials(ActionModule):
    title = _l("Mass import a credential data")
    description = _l("Creates or updates credentials from the transferred file, split according to the specified separator")
    admin_form = None
    run_form = CredentialMultipleAddForm
    exploit_single_target = staticmethod(process_credentials_multiple_import_data)
    exploit = staticmethod(exploit)
    default_options = {}
    show_on_exploit_list = False