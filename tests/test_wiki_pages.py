from app import db
import app.models as models
from flask.testing import FlaskClient
import sqlalchemy as sa
from flask import url_for
from urllib.parse import urlparse


def test_wiki_pages(auth_client: FlaskClient):
    index = auth_client.get(url_for('wiki_pages.pagedirectory_index', _external=False))
    assert index.status_code == 200, f"Cannot open Wiki page index page. Status code is {index.status_code}"
    # Create wiki directory
    new_page_get = auth_client.get(url_for('wiki_pages.pagedirectory_new', _external=False))
    assert new_page_get.status_code == 200, f"Cannot open Wiki pages directory new page. Status code is {new_page_get.status_code}"
    page_data = {"title": "New test page", 'description': 'Page for test', 'parent_directory_id': 0}
    new_pagedirectory_post = auth_client.post(url_for('wiki_pages.pagedirectory_new', _external=False), follow_redirects=True, data=page_data)
    assert new_pagedirectory_post.status_code == 200, f"Cannot create new wiki page directory. Status code is {new_pagedirectory_post.status_code}"
    assert len(new_pagedirectory_post.history) == 1, f"Incorrect count of redirect history after create wiki page directory: {len(new_pagedirectory_post.history)}"
    assert urlparse(new_pagedirectory_post.request.url).path == url_for('wiki_pages.pagedirectory_index', _external=False), f"Incorrect redirect after create new wiki directory page."
    page_directory = db.session.scalars(sa.select(models.WikiDirectory).where(models.WikiDirectory.title == "New test page")).first()
    assert page_directory is not None, f"Cannot create new page directory in database"
    assert "New test page" in new_pagedirectory_post.text, f"New page directory is not on the index page"
    # Create wiki directory via ajax request
    ajax_page_data = {"title": "Another pagedirectory", "description": "Some data", 'parent_dir_id': page_directory.id}
    ajax_new_dir = auth_client.post(url_for('wiki_pages.pagedirectory_ajax_new', _external=False), data=ajax_page_data)
    assert ajax_new_dir.status_code == 200, f"Cannot create new wiki directory via ajax request. Status code: {ajax_new_dir.status_code}. Page_data: {ajax_page_data}, Request: {ajax_new_dir.request.url}"
    assert ajax_new_dir.json["status"] == 'success', f"Unsuccessful create new wiki directory via ajax request"
    assert 'id' in ajax_new_dir.json, f"New directory id not in response after ajax directory create"
    nd = db.session.get(models.WikiDirectory, ajax_new_dir.json["id"])
    assert nd is not None, f"Cannot create new wiki directory via ajax request in database"
    assert getattr(nd, 'title') == ajax_page_data['title'], f"Cannot set a title attribute to wiki directory via ajax request"
    assert getattr(nd, 'description') == ajax_page_data['description'], f"Cannot set a description attribute to wiki directory via ajax request"
    index = auth_client.get(url_for('wiki_pages.pagedirectory_index', _external=False))
    assert index.status_code == 200, f"Cannot show wiki directory index page after create wiki directory via ajax. Status code is {index.status_code}"
    # Edit wiki directory
    new_dir_data = {'title': 'Changed title', 'description': "Changed description"}
    edit_post = auth_client.post(url_for('wiki_pages.pagedirectory_edit', _external=False, wikidirectory_id=nd.id), data=new_dir_data)
    assert edit_post.status_code == 200, f"Cannot edit wiki directory. Status code {edit_post.status_code}"
    assert edit_post.json["status"] == 'success', f"Status of change wiki directory is not success"
    db.session.refresh(nd)
    for key, value in new_dir_data.items():
        assert getattr(nd, key) == value, f"Cannot set attribute {key} to wiki directory after edit request"
    # Delete wiki directory
    delete_post = auth_client.post(url_for('wiki_pages.pagedirectory_delete', wikidirectory_id=nd.id, _external=False))
    assert delete_post.status_code == 200, f"Cannot delete wiki directory. Status code is {delete_post.status_code}"
    assert delete_post.json['status'] == 'success', f"Unsuccessfull delete wiki directory after post request"
    updated_nd = db.session.get(models.WikiDirectory, nd.id)
    assert updated_nd == None, f"Cannot delete wiki directory from database"
    # Create wiki page
    page_data = {'title': 'New page', "description": "Some data", "text": "Some text", "directory_id": page_directory.id}
    create_page_get = auth_client.get(url_for('wiki_pages.wikipage_new', _external=False))
    assert create_page_get.status_code == 200, f"Cannot open wiki page create page. Status code is {create_page_get.status_code}"
    create_page_post = auth_client.post(url_for('wiki_pages.wikipage_new', _external=False), data=page_data, follow_redirects=True)
    assert create_page_post.status_code == 200, f"Cannot create new wiki page. Status code is {create_page_post.status_code}"
    assert len(create_page_post.history) == 1, f"Incorrect count of redirect history after create wiki page: {len(create_page_post.history)}"
    new_page = db.session.scalars(sa.select(models.WikiPage).where(models.WikiPage.title == page_data['title'])).first()
    assert new_page is not None, "Cannot create new wiki page in database"
    assert urlparse(create_page_post.request.url).path == url_for('wiki_pages.wikipage_show', _external=False, wikipage_id=new_page.id), "Incorrect redirect after create new wiki page"
    # Ajax create wiki page
    ajax_page_data = {"parent_dir_id": page_directory.id}
    ajax_new_page = auth_client.post(url_for('wiki_pages.wikipage_ajax_new', _external=False), data=ajax_page_data)
    assert ajax_new_page.status_code == 200, f"Cannot create new wiki page via ajax request. Status code: {ajax_new_page.status_code}. Page_data: {ajax_page_data}, Request: {ajax_new_page.request.url}"
    assert "page_id" in ajax_new_page.json, f"New page id not in response after ajax page create"
    another_page = db.session.scalars(sa.select(models.WikiPage).where(models.WikiPage.id == ajax_new_page.json["page_id"])).first()
    assert another_page is not None, f"Cannot create new wiki page via ajax request in database"
    # Edit wiki page
    wiki_page_edit_get = auth_client.get(url_for('wiki_pages.wikipage_edit', _external=False, wikipage_id=another_page.id))
    assert wiki_page_edit_get.status_code == 200, f"Cannot open wiki page edit page. Status code is {wiki_page_edit_get.status_code}"
    post_data = {"title": "Ajax wiki page", "description": "Ajax wiki page description", "text": "Ajax wiki page text"}
    wiki_page_edit_post = auth_client.post(url_for('wiki_pages.wikipage_edit', _external=False, wikipage_id=another_page.id), data=post_data, follow_redirects=True)
    assert wiki_page_edit_post.status_code == 200, f"Cannot edit wiki page. Status code is {wiki_page_edit_post.status_code}"
    assert len(wiki_page_edit_post.history) == 1, f"Incorrect count of redirect history after edit wiki page: {len(wiki_page_edit_post.history)}"
    assert urlparse(wiki_page_edit_post.request.url).path == url_for('wiki_pages.wikipage_show', _external=False, wikipage_id=another_page.id), "Incorrect redirect after edit wiki page"
    for key, value in post_data.items():
        assert getattr(another_page, key) == value, f"Cannot set attribute {key} to wiki page after edit request"
    ajax_edit_data = {"title": "Ajax edit", "description": "Ajax edit description", "page_id": another_page.id}
    ajax_wiki_page_edit_post = auth_client.post(url_for('wiki_pages.wikipage_ajax_edit', _external=False), data=ajax_edit_data)
    assert ajax_wiki_page_edit_post.status_code == 200, f"Cannot edit wiki page via ajax request. Status code is {ajax_wiki_page_edit_post.status_code}"
    assert "status" in ajax_wiki_page_edit_post.json, f"Status not in response after ajax edit wiki page"
    for key, value in ajax_edit_data.items():
        if key == "page_id":
            continue
        assert getattr(another_page, key) == value, f"Cannot set attribute {key} to wiki page after edit request via ajax"
    index_now = auth_client.get(url_for('wiki_pages.pagedirectory_index', _external=False))
    assert index_now.status_code == 200, f"Cannot open wiki page directory index page after edit some pages. Status code is {index_now.status_code}"
    # Delete wiki page
    ajax_delete = auth_client.post(url_for('wiki_pages.wikipage_ajax_delete', _external=False), data={"page_id": another_page.id}, follow_redirects=True)
    assert ajax_delete.status_code == 200, f"Cannot delete wiki page via ajax request. Status code is {ajax_delete.status_code}"
    assert "status" in ajax_delete.json, f"Status not in response after ajax delete wiki page"
    another_page_after_delete = db.session.scalars(sa.select(models.WikiPage).where(models.WikiPage.id == another_page.id)).first()
    assert another_page_after_delete is None, f"Cannot delete wiki page from database after ajax request"
    normal_delete = auth_client.post(url_for('wiki_pages.wikipage_delete', _external=False, wikipage_id=new_page.id), follow_redirects=True)
    assert normal_delete.status_code == 200, f"Cannot delete wiki page. Status code is {normal_delete.status_code}"
    assert len(normal_delete.history) == 1, f"Incorrect count of redirect history after delete wiki page: {len(normal_delete.history)}"
    assert urlparse(normal_delete.request.url).path == url_for('wiki_pages.pagedirectory_index', _external=False), "Incorrect redirect after delete wiki page"
    new_page_after_delete = db.session.scalars(sa.select(models.WikiPage).where(models.WikiPage.id == new_page.id)).first()
    assert new_page_after_delete is None, f"Cannot delete wiki page from database after normal request"
    # Test wiki ajax structure
    get_wiki_struct = auth_client.get(url_for('wiki_pages.wiki_ajax_struct', _external=False))
    assert get_wiki_struct.status_code == 200, f"Cannot get wiki structure. Status code is {get_wiki_struct.status_code}"
    assert get_wiki_struct.content_type == "application/json", f"Incorrect content type of wiki structure response: {get_wiki_struct.content_type}"