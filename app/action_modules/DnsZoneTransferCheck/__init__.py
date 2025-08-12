from app.action_modules.classes import ActionModule
from app.controllers.forms import FlaskForm, TreeSelectMultipleField
from app import db
import wtforms
import wtforms.validators as validators
from flask_babel import lazy_gettext as _l
import app.models as models
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.orm.session import Session
import dns
import dns.query
import dns.xfr
import logging
logger = logging.getLogger("DNS Zone transfer module")


def action_run(target: models.Service, running_user_id: int, zone_name: str, session: Session, locale: str="en"):
    project_id = target.host.from_network.project_id
    try:
        dns_zone = dns.zone.from_xfr(dns.query.xfr(str(target.host.ip_address), zone_name, port=target.port))
    except dns.xfr.TransferError:
        logger.info(f"Failed transfer for service {target}")
        return []
    logger.info(f"Target has transfer DNS zone: {target}")
    issue_template = session.scalars(sa.select(models.IssueTemplate).where(models.IssueTemplate.string_slug == 'dns_zone_transfer')).first()
    issue_status = session.scalars(sa.select(models.IssueStatus).where(models.IssueStatus.string_slug == 'confirmed')).first()
    if issue_template and issue_status:
        issue = session.scalars(sa.select(models.Issue).where(sa.and_(models.Issue.project_id == project_id, models.Issue.by_template_slug == 'dns_zone_transfer'))).first()
        if issue is None:
            issue = issue_template.create_issue_by_template()
            issue.status = issue_status
            issue.project_id = project_id
            issue.created_by_id = running_user_id
            session.add(issue)
        issue.services.add(target)
    session.commit()
    return list(dns_zone)


def exploit(filled_form: dict, running_user_id: int, default_options: dict, locale: str, project_id: int) -> None:
    logger.info("Running module DNS Zone transfer check")
    with so.sessionmaker(db.engine, autoflush=False)() as session:
        for target in filled_form['targets']:
            target = session.scalars(sa.select(models.Service).where(models.Service.id == int(target))).one()
            logger.info("Trying to exploit " + str(target))
            action_run(target, running_user_id, filled_form["zone_name"], session, locale)
        session.commit()


class AdminOptionsForm(FlaskForm):
    pass


class ModuleInitForm(FlaskForm):
    def __init__(self, project_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dns_mark = db.session.scalars(sa.select(models.AccessProtocol).where(models.AccessProtocol.string_slug == 'domain')).first()
        self.targets.choices = [(str(i.id), i) for i in db.session.scalars(sa.select(models.Service).join(models.Service.host)
                                                                           .join(models.Host.from_network).join(models.Service.access_protocol)
                                                                           .where(sa.and_(models.Network.project_id == project_id, models.Service.access_protocol_id == dns_mark.id,
                                                                                          models.AccessProtocol.string_slug == 'tcp')))]
    targets = TreeSelectMultipleField(_l("Services to scan:"), validators=[validators.InputRequired()])
    zone_name = wtforms.StringField(_l("Zone name:"), validators=[validators.DataRequired(_l("This field is mandatory!")),
                                                                  validators.Length(min=0, max=255, message=_l('This field must not exceed %(length)s characters in length', length=255))])
    wtforms.HiddenField(_l("Project ID:"), validators=[validators.InputRequired()])
    submit = wtforms.SubmitField(_l("Run"))


class DnsZoneTransfer(ActionModule):
    title = _l("DNS Zone Transfer")
    description = _l("Test specified DNS services on zone transfer")
    admin_form = AdminOptionsForm
    run_form = ModuleInitForm
    exploit_single_target = staticmethod(action_run)
    exploit = staticmethod(exploit)
    default_options = {}
