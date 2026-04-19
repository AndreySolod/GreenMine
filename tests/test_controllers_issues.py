"""
Тесты для контроллеров, связанных с проблемами (issues).
"""
import pytest
from app import db
import app.models as models
import sqlalchemy as sa
from flask import url_for
import json
import datetime


class TestIssueControllers:
    """Тесты контроллеров issues."""
    
    def test_issue_index_page(self, auth_client):
        """Тест страницы списка проблем."""
        # Создаем проект
        with auth_client.application.app_context():
            project = models.Project(
                title="Test Project for Index",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
        
        # Запрашиваем страницу
        response = auth_client.get(url_for('issues.issue_index', project_id=project_id))
        assert response.status_code == 200
        assert b'Test Project for Index' in response.data
        
        # Очистка
        with auth_client.application.app_context():
            db.session.delete(db.session.get(models.Project, project_id))
            db.session.commit()
    
    def test_issue_index_data(self, auth_client):
        """Тест API данных для таблицы проблем."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project for Data",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            
            # Создаем статус
            status = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            db.session.add(status)
            db.session.commit()
            
            # Создаем проблему
            issue = models.Issue(
                title="Test Issue for Data",
                description="Test description",
                project_id=project.id,
                status_id=status.id,
                order_number=1
            )
            db.session.add(issue)
            db.session.commit()
        
        # Запрашиваем данные
        response = auth_client.get(url_for('issues.issue_data_index', project_id=project.id))
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'rows' in data
        assert 'total' in data
        
        # Должна быть хотя бы одна проблема
        assert data['total'] >= 1
        
        # Очистка
        with auth_client.application.app_context():
            db.session.delete(db.session.get(models.Issue, issue.id))
            db.session.delete(db.session.get(models.IssueStatus, status.id))
            db.session.delete(db.session.get(models.Project, project.id))
            db.session.commit()
    
    def test_issue_new_page(self, auth_client):
        """Тест страницы создания новой проблемы."""
        with auth_client.application.app_context():
            project = models.Project(
                title="Test Project for New",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
        
        response = auth_client.get(url_for('issues.issue_new', project_id=project.id))
        assert response.status_code == 200
        assert b'Create' in response.data  # Кнопка создания
        
        # Очистка
        with auth_client.application.app_context():
            db.session.delete(db.session.get(models.Project, project.id))
            db.session.commit()
    
    def test_issue_create(self, auth_client):
        """Тест создания проблемы через POST."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project for Create",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            
            # Создаем статус
            status = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            db.session.add(status)
            db.session.commit()
            
            # Создаем CVE
            cve = models.CriticalVulnerability(
                year=2024,
                identifier="CVE-2024-99999",
                cvss=5.0,
                title="Test CVE"
            )
            db.session.add(cve)
            db.session.commit()
        
        # Данные для формы
        form_data = {
            'title': 'New Test Issue',
            'description': '<p>Test description</p>',
            'fix': '<p>Test fix</p>',
            'cvss': '6.5',
            'cve_id': str(cve.id),
            'status_id': str(status.id),
            'submit': 'Create'
        }
        
        # Отправляем POST запрос
        response = auth_client.post(
            url_for('issues.issue_new', project_id=project.id),
            data=form_data,
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Проверяем, что проблема создана в БД
        with auth_client.application.app_context():
            issue = db.session.scalars(
                sa.select(models.Issue).where(
                    models.Issue.title == 'New Test Issue'
                )
            ).first()
            assert issue is not None
            assert issue.project_id == project.id
            assert issue.cvss == 6.5
            
            # Очистка
            db.session.delete(issue)
            db.session.delete(cve)
            db.session.delete(status)
            db.session.delete(project)
            db.session.commit()
    
    def test_issue_show_page(self, auth_client):
        """Тест страницы просмотра проблемы."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project for Show",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            
            # Создаем статус
            status = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            db.session.add(status)
            db.session.commit()
            
            # Создаем проблему
            issue = models.Issue(
                title="Test Issue for Show",
                description="Test description",
                project_id=project.id,
                status_id=status.id
            )
            db.session.add(issue)
            db.session.commit()
        
        # Запрашиваем страницу
        response = auth_client.get(url_for('issues.issue_show', issue_id=issue.id))
        assert response.status_code == 200
        assert b'Test Issue for Show' in response.data
        
        # Очистка
        with auth_client.application.app_context():
            db.session.delete(issue)
            db.session.delete(status)
            db.session.delete(project)
            db.session.commit()
    
    def test_issue_edit_page(self, auth_client):
        """Тест страницы редактирования проблемы."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project for Edit",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            
            # Создаем статус
            status = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            db.session.add(status)
            db.session.commit()
            
            # Создаем проблему
            issue = models.Issue(
                title="Test Issue for Edit",
                description="Test description",
                project_id=project.id,
                status_id=status.id
            )
            db.session.add(issue)
            db.session.commit()
        
        # Запрашиваем страницу редактирования
        response = auth_client.get(url_for('issues.issue_edit', issue_id=issue.id))
        assert response.status_code == 200
        assert b'Save' in response.data  # Кнопка сохранения
        
        # Очистка
        with auth_client.application.app_context():
            db.session.delete(issue)
            db.session.delete(status)
            db.session.delete(project)
            db.session.commit()
    
    def test_issue_update(self, auth_client):
        """Тест обновления проблемы через POST."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project for Update",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            
            # Создаем статусы
            status_open = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            status_closed = models.IssueStatus(
                string_slug="closed",
                title="Closed",
                color="#FF0000"
            )
            db.session.add_all([status_open, status_closed])
            db.session.commit()
            
            # Создаем проблему
            issue = models.Issue(
                title="Original Issue",
                description="Original description",
                project_id=project.id,
                status_id=status_open.id
            )
            db.session.add(issue)
            db.session.commit()
        
        # Данные для формы редактирования
        form_data = {
            'title': 'Updated Issue Title',
            'description': '<p>Updated description</p>',
            'fix': '<p>Updated fix</p>',
            'cvss': '8.0',
            'status_id': str(status_closed.id),
            'submit': 'Save'
        }
        
        # Отправляем POST запрос
        response = auth_client.post(
            url_for('issues.issue_edit', issue_id=issue.id),
            data=form_data,
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Проверяем обновление в БД
        with auth_client.application.app_context():
            updated_issue = db.session.get(models.Issue, issue.id)
            assert updated_issue.title == 'Updated Issue Title'
            assert updated_issue.status_id == status_closed.id
            assert updated_issue.cvss == 8.0
            
            # Очистка
            db.session.delete(updated_issue)
            db.session.delete(status_open)
            db.session.delete(status_closed)
            db.session.delete(project)
            db.session.commit()
    
    def test_issue_delete(self, auth_client):
        """Тест удаления проблемы."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project for Delete",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            
            # Создаем статус
            status = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            db.session.add(status)
            db.session.commit()
            
            # Создаем проблему для удаления
            issue = models.Issue(
                title="Issue to Delete",
                description="Will be deleted",
                project_id=project.id,
                status_id=status.id
            )
            db.session.add(issue)
            db.session.commit()
            issue_id = issue.id
        
        # Отправляем POST запрос на удаление
        response = auth_client.post(
            url_for('issues.issue_delete', issue_id=issue_id),
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Проверяем, что проблема удалена из БД
        with auth_client.application.app_context():
            deleted_issue = db.session.get(models.Issue, issue_id)
            assert deleted_issue is None
            
            # Очистка остального
            db.session.delete(status)
            db.session.delete(project)
            db.session.commit()
    
    def test_issue_archive(self, auth_client):
        """Тест архивации проблемы."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project for Archive",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            
            # Создаем статус
            status = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            db.session.add(status)
            db.session.commit()
            
            # Создаем проблему
            issue = models.Issue(
                title="Issue to Archive",
                description="Will be archived",
                project_id=project.id,
                status_id=status.id,
                archived=False
            )
            db.session.add(issue)
            db.session.commit()
            issue_id = issue.id
        
        # Отправляем POST запрос на архивацию
        response = auth_client.post(
            url_for('issues.issue_archive', issue_id=issue_id),
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Проверяем, что проблема заархивирована
        with auth_client.application.app_context():
            archived_issue = db.session.get(models.Issue, issue_id)
            assert archived_issue.archived is True
            
            # Очистка
            db.session.delete(archived_issue)
            db.session.delete(status)
            db.session.delete(project)
            db.session.commit()
    
    def test_issue_restore(self, auth_client):
        """Тест восстановления проблемы из архива."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project for Restore",
                description="Test",
                start_at=datetime.datetime.now(datetime.UTC).date(),
                end_at=datetime.datetime.now(datetime.UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            
            # Создаем статус
            status = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            db.session.add(status)
            db.session.commit()
            
            # Создаем заархивированную проблему
            issue = models.Issue(
                title="Archived Issue",
                description="Will be restored",
                project_id=project.id,
                status_id=status.id,
                archived=True
            )
            db.session.add(issue)
            db.session.commit()
            issue_id = issue.id
        
        # Отправляем POST запрос на восстановление
        response = auth_client.post(
            url_for('issues.issue_restore', issue_id=issue_id),
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Проверяем, что проблема восстановлена
        with auth_client.application.app_context():
            restored_issue = db.session.get(models.Issue, issue_id)
            assert restored_issue.archived is False
            
            # Очистка
            db.session.delete(restored_issue)
            db.session.delete(status)
            db.session.delete(project)
            db.session.commit()


class TestIssueTemplates:
    """Тесты для шаблонов проблем."""
    
    def test_issue_template_index(self, auth_client):
        """Тест страницы списка шаблонов проблем."""
        response = auth_client.get(url_for('issues.issue_template_index'))
        assert response.status_code == 200
    
    def test_issue_template_new_page(self, auth_client):
        """Тест страницы создания нового шаблона."""
        response = auth_client.get(url_for('issues.issue_template_new'))
        assert response.status_code == 200
        assert b'Create' in response.data
    
    def test_issue_template_create(self, auth_client):
        """Тест создания шаблона проблемы."""
        form_data = {
            'title': 'New Test Template',
            'description': '<p>Template description</p>',
            'fix': '<p>Template fix</p>',
            'technical': '<p>Technical info</p>',
            'riscs': '<p>Risks</p>',
            'references': '<p>References</p>',
            'cvss': '7.0',
            'submit': 'Create'
        }
        
        response = auth_client.post(
            url_for('issues.issue_template_new'),
            data=form_data,
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Проверяем создание в БД
        with auth_client.application.app_context():
            template = db.session.scalars(
                sa.select(models.IssueTemplate).where(
                    models.IssueTemplate.title == 'New Test Template'
                )
            ).first()
            assert template is not None
            assert template.cvss == 7.0
            
            # Очистка
            db.session.delete(template)
            db.session.commit()


if __name__ == "__main__":
    pytest.main([__file__])