import wtforms
from wtforms import validators
import app.models as models
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.orm.session import Session
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from app.controllers.forms import FlaskForm, TreeSelectMultipleField
from app.action_modules.classes import ActionModule
from app import db
import logging
from flask_babel import lazy_gettext as _l
logger = logging.getLogger('Module_Inner_enumerate')


def action_run(target: models.Service, running_user_id: int, protocol: str, window_size: str, timeout: str, implicity_wait: str, session: Session) -> bool:
    ''' Gets a screenshot of the web service and saves it to the database '''
    print('take screenshot of:', target.ip_address, target.port)
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument(f'--window-size={window_size}') # 1920,2500
    chrome_options.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(int(timeout))
    driver.implicitly_wait(int(implicity_wait))
    driver.get(f"{protocol}://{target.host.ip_address}:{target.port}")
    png_data = driver.get_screenshot_as_png()
    if (protocol == 'http'):
        if target.screenshot_http is not None:
            session.delete(target.screenshot_http)
            session.commit()
        fd = models.FileData(title=f"Screenshot {protocol}://{target.host.ip_address}:{target.port}.png", extension='png', data=png_data, created_by_id=running_user_id)
        session.add(fd)
        target.screenshot_http = fd
    else:
        if target.screenshot_https is not None:
            session.delete(target.screenshot_https)
            session.commit()
        fd = models.FileData(title=f"Screenshot {protocol}://{target.host.ip_address}:{target.port}.png", extension='png', data=png_data, created_by_id=running_user_id)
        session.add(fd)
        target.screenshot_https = fd
    attr = "screenshot_" + protocol
    session.add(target)
    print('commit of add target and fd')
    session.commit()
    print('session committed')


def exploit(filled_form: dict, running_user_id: int, default_options: dict, locale: str='en') -> None:
    ''' Retrieves screenshots from the web services specified in the completed filled_form form and saves them to the database '''
    logger.info(f"Running module <Inner enumerate> by ID: {running_user_id}")
    with so.sessionmaker(bind=db.engine)() as session:
        for i in filled_form["targets"]:
            service = session.scalars(sa.select(models.Service).where(models.Service.id == i)).one()
            if filled_form["check_proto"]:
                if service.access_protocol.string_slug in ('http', 'https'):
                    # clean old screenshots from database
                    attr = "screenshot_" + service.access_protocol.string_slug
                    if getattr(service, attr) is not None:
                        session.delete(getattr(service, attr))
                        session.commit()
                    # Taking screenshot
                    try:
                        action_run(target=service, running_user_id=running_user_id, protocol=service.access_protocol.string_slug,
                                window_size=default_options["window_size"], timeout=default_options["timeout"], implicity_wait=default_options["implicity_wait"],
                                session=session)
                    except WebDriverException:
                        continue
            else:
                for protocol in ('http', 'https'):
                    # clean old screenshots from database
                    attr = "screenshot_" + protocol
                    if getattr(service, attr) is not None:
                        session.delete(getattr(service, attr))
                        session.commit()
                    # Taking screenshot
                    try:
                        action_run(target=service, running_user_id=running_user_id, protocol=protocol,
                                window_size=default_options["window_size"], timeout=default_options["timeout"], implicity_wait=default_options["implicity_wait"],
                                session=session)
                    except WebDriverException:
                        continue


class AdminOptionsForm(FlaskForm):
    window_size = wtforms.StringField(_l("Dimensions of the created image (in pixels):"), validators=[validators.DataRequired(message=_l("This field is mandatory!"))], default="1920,2500")
    timeout = wtforms.IntegerField(_l("Page loading timeout:"), validators=[validators.DataRequired(message=_l("This field is mandatory!"))], default=30)
    implicity_wait = wtforms.IntegerField(_l("Page loading wait:"), validators=[validators.DataRequired(message=_l("This field is mandatory!"))], default=5)
    submit = wtforms.SubmitField(_l("Save"))
    
    def validate_window_size(form, field):
        window_size = field.data.split(',')
        if len(window_size) != 2:
            raise wtforms.ValidationError(_l("The dimensions of the created image should be set in the form of 'Width, Height'"))
        try:
            ws1 = int(window_size[0])
            ws2 = int(window_size[1])
            if ws1 <= 0 or ws2 <= 0:
                raise wtforms.ValidationError(_l("The dimensions of the created image must be set as a positive number of pixels"))
        except (ValueError, TypeError):
            raise wtforms.ValidationError(_l("The dimensions of the created image must be set in pixels. Example: '1920.2500'"))
    
    def validate_timeout(form, field):
        if field.data <= 0:
            raise wtforms.ValidationError(_l("The page load timeout must be greater than 0!"))


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.targets.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).join(models.Service.host)
                                                                           .join(models.Host.from_network).join(models.Service.access_protocol).where(sa.and_(models.Network.project_id==project_id,
                                                                                                                                                              models.AccessProtocol.string_slug.ilike("http%"))))]
    targets = TreeSelectMultipleField(_l("Target verification range:"), validators=[validators.Optional()])
    check_proto = wtforms.BooleanField(_l("Check proto - use only http/https:"), default=True)
    submit = wtforms.SubmitField(_l("Run"))


class HardwareInventory(ActionModule):
    title = _l("Inventory Manager")
    description = _l("For a given address, if the http/https protocol is used, it receives a screenshot of the site and returns it in binary form")
    admin_form = AdminOptionsForm
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {'window_size': '1920,2500', 'timeout': 5, 'implicity_wait': 5}
