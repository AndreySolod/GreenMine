from app import db
from app.helpers.general_helpers import default_string_slug, utcnow
from app.helpers.admin_helpers import project_enumerated_object, project_object_with_permissions
from typing import List, Optional, Set
import datetime
from .generic import HasComment, HasHistory
from .datatypes import LimitedLengthString
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.ext.hybrid import hybrid_property
import wtforms
from app.controllers.forms import PickrColorField
from sqlalchemy import event
from sqlalchemy.orm.session import Session as SessionBase
from flask_babel import lazy_gettext as _l


@project_enumerated_object
class IssueStatus(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l('Slug')})
    title: so.Mapped[str] = so.mapped_column(sa.String(40), info={'label': _l('Title')})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l('State description'), 'form': wtforms.TextAreaField})
    color: so.Mapped[str] = so.mapped_column(sa.String(60), info={'label': _l('Color'), 'form': PickrColorField})

    class Meta:
        verbose_name = _l('Issue status')
        verbose_name_plural = _l('Issue statuses')
        title_new = _l('Add issue status')
        column_index = ['id', 'string_slug', 'title', 'description', 'color']


@project_enumerated_object
class VulnerableEnvironmentType(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l('Slug')})
    title: so.Mapped[str] = so.mapped_column(sa.String(20), info={'label': _l('Title')})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l('Description')})

    class Meta:
        verbose_name = _l('Type of vulnerable environment')
        verbose_name_plural = _l('Types of vulnerable environment')
        title_new = _l('Add new type of vulnerable environment')
        column_index = ["id", "string_slug", "title", "description"]


class CriticalVulnerability(HasComment, db.Model, HasHistory):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    created_at: so.Mapped[datetime.datetime] = so.mapped_column(default=utcnow, index=True, info={'label': _l('Created at')})
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l('Created by')})
    created_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys="CriticalVulnerability.created_by_id", info={'label': _l('Created by')}) # type: ignore
    updated_at: so.Mapped[Optional[datetime.datetime]] = so.mapped_column(info={"label": _l('Updated at')})
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete="SET NULL"), info={'label': _l('Updated by')})
    updated_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys="CriticalVulnerability.updated_by_id", info={'label': _l('Updated by')}) # type: ignore
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l('Archived')})
    year: so.Mapped[int] = so.mapped_column(default=lambda: datetime.datetime.now(datetime.UTC).year, info={'label': _l('The year the vulnerability was released')})
    identifier: so.Mapped[str] = so.mapped_column(sa.String(20), info={'label': _l('CVE identifier')})
    cvss: so.Mapped[float] = so.mapped_column(info={'label': _l('CVSS')})
    title: so.Mapped[int] = so.mapped_column(sa.String(50), info={'label': _l('Title')})
    description: so.Mapped[str] = so.mapped_column(info={'label': _l('Description')})
    vulnerable_environment_type_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(VulnerableEnvironmentType.id, ondelete='SET NULL'), info={'label': _l('Type of vulnerable environment')})
    vulnerable_environment_type: so.Mapped[VulnerableEnvironmentType] = so.relationship(lazy='joined', info={'label': _l('Type of vulnerable environment')})
    vulnerable_environment: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l('Vulnerable environment creation script')})
    proof_of_concept_language_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('programming_language.id', ondelete='SET NULL'), info={'label': _l('Proof of Concept language')})
    proof_of_concept_language: so.Mapped["ProgrammingLanguage"] = so.relationship(lazy='joined', info={'label': _l('Proof of Concept language')}) # type: ignore
    proof_of_concept_code: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l('Proof of Concept')})
    wikipage_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('wiki_page.id', ondelete='SET NULL'), info={'label': _l('Page in Wiki')})
    wikipage: so.Mapped["WikiPage"] = so.relationship(lazy='select', info={'label': _l("Page in Wiki")}) # type: ignore

    __table_args__ = (sa.UniqueConstraint('year', 'identifier', name='_unique_year_and_identifier_together'),)

    class Meta:
        verbose_name = _l('Critical vulnerability')
        verbose_name_plural = _l('Critical vulnerabilities')


class ProofOfConcept(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    archived: so.Mapped[bool] = so.mapped_column(default=False)
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, default=default_string_slug)
    title: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50))
    description: so.Mapped[str]
    source_code: so.Mapped[str]
    source_code_language_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('programming_language.id', ondelete='SET NULL'), nullable=False)
    source_code_language: so.Mapped["ProgrammingLanguage"] = so.relationship(lazy='joined') # type: ignore

    class Meta:
        verbose_name = _l('Proof of Concept')
        verbose_name_plural = _l('Proofs of Concept')


class IssueHasService(db.Model):
    service_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('service.id', ondelete='CASCADE'), primary_key=True)
    issue_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('issue.id', ondelete='CASCADE'), primary_key=True)


class IssueHasTask(db.Model):
    issue_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('issue.id', ondelete='CASCADE'), primary_key=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project_task.id', ondelete='CASCADE'), primary_key=True)


@project_object_with_permissions
class Issue(HasComment, db.Model, HasHistory):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l('Archived')})
    by_template_slug: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Created by template")}) # Used for create issue from nmap scripts
    created_at: so.Mapped[datetime.datetime] = so.mapped_column(default=utcnow, info={"label": _l("Created at")})
    created_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete='SET NULL'), info={'label': _l("Created by")})
    created_by: so.Mapped["User"] = so.relationship(lazy='select', foreign_keys="Issue.created_by_id", info={'label': _l("Created by")}) # type: ignore
    updated_at: so.Mapped[Optional[datetime.datetime]] = so.mapped_column(info={"label": _l("Updated at")})
    updated_by_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('user.id', ondelete="SET NULL"), info={'label': _l("Updated by")})
    updated_by: so.Mapped['User'] = so.relationship(lazy='select', foreign_keys="Issue.updated_by_id", info={'label': _l("Updated by")}) # type: ignore
    title: so.Mapped[str] = so.mapped_column(sa.String(100), info={'label': _l("Title")})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Description")})
    fix: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Fix")})
    technical: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Technical information")})
    riscs: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Exploitation riscs")})
    references: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Links to additional information")})
    cvss: so.Mapped[Optional[float]] = so.mapped_column(info={'label': _l('CVSS')})
    cve_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(CriticalVulnerability.id, ondelete='SET NULL'), info={'label': _l('CVE')})
    cve: so.Mapped['CriticalVulnerability'] = so.relationship(lazy='joined', info={'label': _l('CVE')})
    status_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('issue_status.id', ondelete='SET NULL'), info={'label': _l('Status')})
    status: so.Mapped['IssueStatus'] = so.relationship(lazy='joined', info={'label': _l('Status')})
    services: so.Mapped[Set["Service"]] = so.relationship(secondary=IssueHasService.__table__, # type: ignore
                                                                     primaryjoin='Issue.id==IssueHasService.issue_id',
                                                                     secondaryjoin='Service.id==IssueHasService.service_id',
                                                                     back_populates="issues",
                                                                     info={'label': _l('Related services')})
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('project.id', ondelete="CASCADE"), info={'label': _l("Project")})
    project: so.Mapped["Project"] = so.relationship(lazy='select', backref=db.backref('issues', cascade='all, delete-orphan'), info={'label': _l("Project")}) # type: ignore
    tasks_by_issue: so.Mapped[List["ProjectTask"]] = so.relationship(secondary=IssueHasTask.__table__, # type: ignore
                                                                     primaryjoin='Issue.id==IssueHasTask.issue_id',
                                                                     secondaryjoin='ProjectTask.id==IssueHasTask.task_id',
                                                                     back_populates="issues",
                                                                     info={'label': _l("Related tasks")})
    proof_of_concept_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(ProofOfConcept.id, ondelete='SET NULL'), info={'label': _l("Proof of Concept")})
    proof_of_concept: so.Mapped['ProofOfConcept'] = so.relationship(lazy='select', info={'label': _l("Proof of Concept")})

    @property
    def fulltitle(self):
        return _l("Issue #%(issue_id)s: «%(issue_title)s»", issue_id=self.id, issue_title=self.title)
    
    @property
    def treeselecttitle(self):
        return self.fulltitle

    class Meta:
        verbose_name = _l('Issue')
        verbose_name_plural = _l('Issues')
        icon = 'fa-solid fa-id-card'
        icon_index = 'fa-solid fa-id-card'
        project_permission_actions = {'index': _l("Show object list"), 'create': _l("Create new object"), 'show': _l("Show object card"),
                                      'update': _l("Edit and update object"), 'delete': _l("Delete object"), 'add_comment': _l("Add comment to object"),
                                      'show_comments': _l("Show comment list of object"), 'show_history': _l("Show object history")}

    @property
    def service_list_as_text(self):
        return '\n'.join([i.shorttitle for i in self.services])


class IssueTemplate(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True, info={'label': _l('ID')})
    archived: so.Mapped[bool] = so.mapped_column(default=False, info={'label': _l('Archived')})
    string_slug: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, default=default_string_slug, info={'label': _l('Slug')})
    title: so.Mapped[str] = so.mapped_column(sa.String(100), info={'label': _l('Template title')})
    description: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l('Template Description')})
    issue_title: so.Mapped[str] = so.mapped_column(LimitedLengthString(Issue.title.type.length), info={'label': _l('Issue Title')})
    issue_description: so.Mapped[str] = so.mapped_column(info={'label': _l('Issue Description')})
    issue_fix: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l('Issue fix')})
    issue_technical: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Technical information about issue")})
    issue_riscs: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Issue exploitation riscs")})
    issue_references: so.Mapped[Optional[str]] = so.mapped_column(info={'label': _l("Issue links to additional information")})
    issue_cvss: so.Mapped[Optional[float]] = so.mapped_column(info={'label': _l('Issue CVSS')})
    issue_cve_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(CriticalVulnerability.id, ondelete='SET NULL'), info={'label': _l('Issue CVE')})
    issue_cve: so.Mapped['CriticalVulnerability'] = so.relationship(lazy='joined', info={'label': _l('Issue CVE')})

    def create_issue_by_template(self) -> Issue:
        issue = Issue(title = self.issue_title, description=self.issue_description, fix=self.issue_fix)
        issue.technical = self.issue_technical
        issue.riscs = self.issue_riscs
        issue.references = self.issue_references
        issue.cvss = self.issue_cvss
        issue.cve_id = self.issue_cve_id
        issue.by_template_slug = self.string_slug
        return issue

    class Meta:
        verbose_name = _l('Issue template')
        verbose_name_plural = _l('Issue templates')
        icon = 'fa-solid fa-passport'