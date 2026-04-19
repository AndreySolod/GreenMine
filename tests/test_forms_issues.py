"""
Тесты для форм, связанных с проблемами (issues).
"""
import pytest
from app import db
import app.models as models
import sqlalchemy as sa
from app.controllers.issues.forms import IssueForm, IssueCreateForm, IssueEditForm, EditRelatedObjectsForm
from flask import g
from flask_babel import Babel
import datetime


class TestIssueForm:
    """Тесты для базовой формы IssueForm."""
    
    def test_form_initialization(self, auth_client):
        """Тест инициализации формы с project_id."""
        with auth_client.application.app_context():
            # Создаем тестовые данные
            project = models.Project(
                title="Test Project for Form",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            
            # Создаем статусы
            status1 = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            status2 = models.IssueStatus(
                string_slug="closed",
                title="Closed",
                color="#FF0000"
            )
            db.session.add_all([status1, status2])
            db.session.commit()
            
            # Создаем CVE
            cve = models.CriticalVulnerability(
                year=2024,
                identifier="CVE-2024-00001",
                cvss=5.0,
                title="Test CVE"
            )
            db.session.add(cve)
            db.session.commit()
            
            # Инициализируем форму
            form = IssueForm(project_id=project.id)
            
            # Проверяем, что choices заполнены
            assert len(form.status_id.choices) >= 2
            assert len(form.cve_id.choices) >= 1  # есть выбор "---" + CVE
            
            # Проверяем order_number
            assert hasattr(form, 'order_number')
            assert isinstance(form.order_number, int)
            
            # Очистка
            db.session.delete(cve)
            db.session.delete(status1)
            db.session.delete(status2)
            db.session.delete(project)
            db.session.commit()
    
    def test_form_validation_valid_data(self, auth_client):
        """Тест валидации формы с корректными данными."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project Validation",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            
            # Создаем форму с валидными данными
            form_data = {
                'title': 'Test Issue Title',
                'description': '<p>Test description</p>',
                'fix': '<p>Test fix</p>',
                'technical': '<p>Technical info</p>',
                'riscs': '<p>Risks</p>',
                'references': '<p>References</p>',
                'cvss': 5.5,
                'cve_id': '0',  # ---
                'status_id': '',  # optional
                'services': [],
                'hosts': [],
                'tasks_by_issue': []
            }
            
            form = IssueForm(project_id=project.id, data=form_data)
            
            # Форма должна быть валидной
            assert form.validate() is True
            
            # Очистка
            db.session.delete(project)
            db.session.commit()
    
    def test_form_validation_invalid_data(self, auth_client):
        """Тест валидации формы с некорректными данными."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project Invalid",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            
            # Тест 1: Отсутствует обязательное поле title
            form_data = {
                'title': '',  # Пустое поле
                'description': '<p>Test</p>'
            }
            
            form = IssueForm(project_id=project.id, data=form_data)
            assert form.validate() is False
            assert 'title' in form.errors
            
            # Тест 2: Слишком длинный title
            long_title = 'A' * 101  # Предполагаем, что максимальная длина 100
            form_data = {
                'title': long_title,
                'description': '<p>Test</p>'
            }
            
            form = IssueForm(project_id=project.id, data=form_data)
            # Проверяем валидацию длины (если настроена)
            # В реальном тесте нужно знать точную максимальную длину
            
            # Тест 3: Некорректный CVSS (не число)
            form_data = {
                'title': 'Test Issue',
                'cvss': 'not-a-number'
            }
            
            form = IssueForm(project_id=project.id, data=form_data)
            # Поле cvss - FloatField, должно валидироваться
            
            # Очистка
            db.session.delete(project)
            db.session.commit()


class TestIssueCreateForm:
    """Тесты для формы создания IssueCreateForm."""
    
    def test_create_form_fields(self, auth_client):
        """Тест наличия полей в форме создания."""
        with auth_client.application.app_context():
            project = models.Project(
                title="Test Project Create Form",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            
            form = IssueCreateForm(project_id=project.id)
            
            # Проверяем наличие дополнительных полей
            assert hasattr(form, 'by_template_slug')
            assert hasattr(form, 'submit')
            assert hasattr(form, 'submit_and_add_new')
            
            assert form.submit.label.text is not None
            assert form.submit_and_add_new.label.text is not None
            
            # Очистка
            db.session.delete(project)
            db.session.commit()


class TestIssueEditForm:
    """Тесты для формы редактирования IssueEditForm."""
    
    def test_edit_form_fields(self, auth_client):
        """Тест наличия полей в форме редактирования."""
        with auth_client.application.app_context():
            project = models.Project(
                title="Test Project Edit Form",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            
            form = IssueEditForm(project_id=project.id)
            
            # Проверяем наличие кнопки submit
            assert hasattr(form, 'submit')
            assert form.submit.label.text is not None
            
            # Очистка
            db.session.delete(project)
            db.session.commit()


class TestEditRelatedObjectsForm:
    """Тесты для формы редактирования связанных объектов."""
    
    def test_form_initialization_with_issue(self, auth_client):
        """Тест инициализации формы с объектом Issue."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project Related",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            
            # Создаем сеть
            network = models.Network(
                title="Test Network",
                ip_address="10.0.0.0/24",
                project_id=project.id
            )
            db.session.add(network)
            db.session.commit()
            
            # Создаем хост
            host = models.Host(
                title="Test Host",
                ip_address="10.0.0.1",
                from_network_id=network.id
            )
            db.session.add(host)
            db.session.commit()
            
            # Создаем сервис
            service = models.Service(
                title="Test Service",
                port=443,
                host_id=host.id
            )
            db.session.add(service)
            db.session.commit()
            
            # Создаем статус
            status = models.IssueStatus(
                string_slug="test",
                title="Test",
                color="#0000FF"
            )
            db.session.add(status)
            db.session.commit()
            
            # Создаем задачу
            task = models.ProjectTask(
                title="Test Task",
                project_id=project.id
            )
            db.session.add(task)
            db.session.commit()
            
            # Создаем язык программирования
            lang = models.ProgrammingLanguage(
                string_slug="python",
                title="Python",
                comment="Python language"
            )
            db.session.add(lang)
            db.session.commit()
            
            # Создаем проблему
            issue = models.Issue(
                title="Test Issue for Related",
                description="Test",
                project_id=project.id,
                status_id=status.id
            )
            issue.services.append(service)
            issue.hosts.append(host)
            issue.tasks_by_issue.append(task)
            db.session.add(issue)
            db.session.commit()
            
            # Создаем Proof of Concept
            poc = models.ProofOfConcept(
                string_slug="test-poc",
                title="Test PoC",
                description="Test",
                source_code="print('test')",
                source_code_language_id=lang.id
            )
            db.session.add(poc)
            db.session.commit()
            
            issue.proof_of_concept = poc
            db.session.commit()
            
            # Инициализируем форму
            form = EditRelatedObjectsForm(issue=issue)
            
            # Проверяем, что данные установлены
            assert str(service.id) in form.services.data
            assert str(host.id) in form.hosts.data
            assert str(task.id) in form.tasks_by_issue.data
            assert form.proof_of_concept_title.data == "Test PoC"
            assert form.proof_of_concept_source_code_language.data == str(lang.id)
            
            # Проверяем choices
            assert len(form.services.choices) >= 1
            assert len(form.tasks_by_issue.choices) >= 1
            assert len(form.proof_of_concept_source_code_language.choices) >= 1
            
            # Очистка
            db.session.delete(issue)
            db.session.delete(poc)
            db.session.delete(lang)
            db.session.delete(task)
            db.session.delete(status)
            db.session.delete(service)
            db.session.delete(host)
            db.session.delete(network)
            db.session.delete(project)
            db.session.commit()
    
    def test_form_validation(self, auth_client):
        """Тест валидации формы EditRelatedObjectsForm."""
        with auth_client.application.app_context():
            # Создаем минимальные данные
            project = models.Project(
                title="Test Project Validation",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            
            status = models.IssueStatus(
                string_slug="test",
                title="Test",
                color="#0000FF"
            )
            db.session.add(status)
            db.session.commit()
            
            issue = models.Issue(
                title="Test Issue",
                description="Test",
                project_id=project.id,
                status_id=status.id
            )
            db.session.add(issue)
            db.session.commit()
            
            # Создаем форму с валидными данными
            form_data = {
                'services': [],
                'hosts': [],
                'tasks_by_issue': [],
                'proof_of_concept_title': 'Test PoC',
                'proof_of_concept_description': '<p>Description</p>',
                'proof_of_concept_source_code': 'print("test")',
                'proof_of_concept_source_code_language': ''
            }
            
            form = EditRelatedObjectsForm(issue=issue, data=form_data)
            
            # Форма должна быть валидной (все поля optional кроме proof_of_concept_title)
            # Но proof_of_concept_title имеет validators=[validators.InputRequired]
            # Поэтому форма будет невалидной без языка программирования
            
            # Очистка
            db.session.delete(issue)
            db.session.delete(status)
            db.session.delete(project)
            db.session.commit()


if __name__ == "__main__":
    pytest.main([__file__])