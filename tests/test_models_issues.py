"""
Тесты для моделей, связанных с проблемами (issues).
"""
import pytest
from app import db
import app.models as models
import sqlalchemy as sa
from datetime import datetime, UTC


class TestIssueStatus:
    """Тесты для модели IssueStatus."""
    
    def test_create_issue_status(self, auth_client):
        """Тест создания статуса проблемы."""
        with auth_client.application.app_context():
            # Создаем новый статус
            status = models.IssueStatus(
                string_slug="test-status",
                title="Test Status",
                description="Test description",
                color="#FF0000"
            )
            db.session.add(status)
            db.session.commit()
            
            # Проверяем, что статус создан
            saved_status = db.session.scalars(
                sa.select(models.IssueStatus).where(
                    models.IssueStatus.string_slug == "test-status"
                )
            ).first()
            
            assert saved_status is not None
            assert saved_status.title == "Test Status"
            assert saved_status.color == "#FF0000"
            
            # Очистка
            db.session.delete(saved_status)
            db.session.commit()
    
    def test_issue_status_required_fields(self, auth_client):
        """Тест обязательных полей статуса проблемы."""
        with auth_client.application.app_context():
            # Попытка создать статус без обязательных полей
            status = models.IssueStatus()
            db.session.add(status)
            
            with pytest.raises(Exception):
                db.session.commit()
            
            db.session.rollback()


class TestCriticalVulnerability:
    """Тесты для модели CriticalVulnerability."""
    
    def test_create_critical_vulnerability(self, auth_client):
        """Тест создания критической уязвимости."""
        with auth_client.application.app_context():
            # Создаем тип уязвимой среды
            env_type = models.VulnerableEnvironmentType(
                string_slug="test-env",
                title="Test Environment"
            )
            db.session.add(env_type)
            db.session.commit()
            
            # Создаем уязвимость
            cve = models.CriticalVulnerability(
                year=2024,
                identifier="CVE-2024-00001",
                cvss=7.5,
                title="Test Vulnerability",
                description="Test description",
                vulnerable_environment_type_id=env_type.id
            )
            db.session.add(cve)
            db.session.commit()
            
            # Проверяем создание
            saved_cve = db.session.scalars(
                sa.select(models.CriticalVulnerability).where(
                    models.CriticalVulnerability.identifier == "CVE-2024-00001"
                )
            ).first()
            
            assert saved_cve is not None
            assert saved_cve.cvss == 7.5
            assert saved_cve.vulnerable_environment_type.title == "Test Environment"
            
            # Очистка
            db.session.delete(saved_cve)
            db.session.delete(env_type)
            db.session.commit()
    
    def test_cvss_validation(self, auth_client):
        """Тест валидации CVSS."""
        with auth_client.application.app_context():
            # Создаем уязвимость с некорректным CVSS
            cve = models.CriticalVulnerability(
                year=2024,
                identifier="CVE-2024-00002",
                cvss=15.0,  # Некорректное значение
                title="Test Vulnerability"
            )
            db.session.add(cve)
            
            # Проверяем, что валидация сработает
            with pytest.raises(ValueError):
                db.session.commit()
            
            db.session.rollback()
            
            # Создаем с корректным CVSS
            cve.cvss = 5.0
            db.session.add(cve)
            db.session.commit()
            
            # Очистка
            db.session.delete(cve)
            db.session.commit()


class TestProofOfConcept:
    """Тесты для модели ProofOfConcept."""
    
    def test_create_proof_of_concept(self, auth_client):
        """Тест создания Proof of Concept."""
        with auth_client.application.app_context():
            # Создаем язык программирования
            lang = models.ProgrammingLanguage(
                string_slug="python",
                title="Python",
                comment="Python language"
            )
            db.session.add(lang)
            db.session.commit()
            
            # Создаем PoC
            poc = models.ProofOfConcept(
                string_slug="test-poc",
                title="Test PoC",
                description="Test description",
                source_code="print('Hello')",
                source_code_language_id=lang.id
            )
            db.session.add(poc)
            db.session.commit()
            
            # Проверяем создание
            saved_poc = db.session.scalars(
                sa.select(models.ProofOfConcept).where(
                    models.ProofOfConcept.string_slug == "test-poc"
                )
            ).first()
            
            assert saved_poc is not None
            assert saved_poc.title == "Test PoC"
            assert saved_poc.source_code_language.title == "Python"
            
            # Очистка
            db.session.delete(saved_poc)
            db.session.delete(lang)
            db.session.commit()


class TestIssue:
    """Тесты для модели Issue."""
    
    def test_create_issue(self, auth_client):
        """Тест создания проблемы."""
        with auth_client.application.app_context():
            # Создаем необходимые зависимости
            project = models.Project(
                title="Test Project for Issue",
                description="Test description",
                start_at=datetime.now(UTC).date(),
                end_at=datetime.now(UTC).date(),
                leader_id=1  # admin user
            )
            db.session.add(project)
            db.session.commit()
            
            status = models.IssueStatus(
                string_slug="open",
                title="Open",
                color="#00FF00"
            )
            db.session.add(status)
            db.session.commit()
            
            # Создаем проблему
            issue = models.Issue(
                title="Test Issue",
                description="Test issue description",
                project_id=project.id,
                status_id=status.id,
                order_number=1
            )
            db.session.add(issue)
            db.session.commit()
            
            # Проверяем создание
            saved_issue = db.session.scalars(
                sa.select(models.Issue).where(
                    models.Issue.title == "Test Issue"
                )
            ).first()
            
            assert saved_issue is not None
            assert saved_issue.project.title == "Test Project for Issue"
            assert saved_issue.status.title == "Open"
            assert saved_issue.order_number == 1
            
            # Очистка
            db.session.delete(saved_issue)
            db.session.delete(status)
            db.session.delete(project)
            db.session.commit()
    
    def test_issue_relationships(self, auth_client):
        """Тест связей проблемы с сервисами и хостами."""
        with auth_client.application.app_context():
            # Создаем проект
            project = models.Project(
                title="Test Project for Relationships",
                description="Test",
                start_at=datetime.now(UTC).date(),
                end_at=datetime.now(UTC).date(),
                leader_id=1
            )
            db.session.add(project)
            db.session.commit()
            
            # Создаем сеть
            network = models.Network(
                title="Test Network",
                ip_address="192.168.1.0/24",
                project_id=project.id
            )
            db.session.add(network)
            db.session.commit()
            
            # Создаем хост
            host = models.Host(
                title="Test Host",
                ip_address="192.168.1.1",
                from_network_id=network.id
            )
            db.session.add(host)
            db.session.commit()
            
            # Создаем сервис
            service = models.Service(
                title="Test Service",
                port=80,
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
            
            # Создаем проблему
            issue = models.Issue(
                title="Test Issue with Relationships",
                description="Test",
                project_id=project.id,
                status_id=status.id
            )
            issue.services.append(service)
            issue.hosts.append(host)
            db.session.add(issue)
            db.session.commit()
            
            # Проверяем связи
            saved_issue = db.session.get(models.Issue, issue.id)
            assert len(saved_issue.services) == 1
            assert saved_issue.services[0].title == "Test Service"
            assert len(saved_issue.hosts) == 1
            assert saved_issue.hosts[0].title == "Test Host"
            
            # Очистка
            db.session.delete(saved_issue)
            db.session.delete(status)
            db.session.delete(service)
            db.session.delete(host)
            db.session.delete(network)
            db.session.delete(project)
            db.session.commit()


if __name__ == "__main__":
    pytest.main([__file__])