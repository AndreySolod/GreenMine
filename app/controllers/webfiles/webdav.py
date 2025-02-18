from app import db
from app.controllers.webfiles import bp
import app.models as models
import sqlalchemy as sa
from flask import request
from flask import abort, render_template, make_response


@bp.route("/webdav/<int:project_id>/<path:pathname>", methods=["GET"]) # /webdav/1/root/ - this is a root directory
def get_path_content(project_id: int, pathname: str):
    project = db.get_or_404(models.Project, project_id)
    path = pathname.split('/')[1::]
    root_dir = project.file_directories[0]
    current_dir = root_dir
    for p_number, p in enumerate(path):
        print('p is:', p, 'p_number:', p_number)
        if p == "." or p == 'root':
            continue
        elif p == "..":
            current_dir = current_dir.parent
        if p == "" and p_number == len(path) - 1:
            # Finish: this is a path and requested a path
            uri_prefix = "/".join(path[:p_number + 1:])
            link_list = [uri_prefix + i for i in db.session.scalars(sa.select(models.FileData.title).where(models.FileData.directory_id == current_dir.id)
                                                                    .union(sa.select(models.FileDirectory.title).where(models.FileDirectory.parent_dir_id == current_dir.id))).all()]
            return render_template("webfiles/webdav_get_collections.html", link_list=link_list) # returned an directory 
        current_dir = db.session.scalars(sa.select(models.FileDirectory).where(sa.and_(models.FileDirectory.title == p, models.FileDirectory.parent_dir_id == root_dir.id))).first()
        if current_dir is None and p_number == len(path) - 1:
            # End: this is a last directory, and looks like user request a file
            current_file = db.session.scalars(sa.select(models.FileData).where(sa.and_(models.FileData.title == p, models.FileData.directory_id == root_dir.id))).first()
            if current_file is None:
                abort(404)
            response = make_response(current_file.data)
            return response # Returned file with his mime type
        elif current_dir is None:
            # Path is not end, but current dir is none - this directory is unexist
            abort(404)
        else:
            root_dir = current_dir


@bp.route("/webdav/<int:project_id>/<path:pathname>", methods=['PROPFIND'])
def propfind_path_content(project_id: int, pathname: str):
    # First request of all webdav client is propfind
    path = pathname.split("/")[1::]
    ''' Запрос: <?xml version="1.0" encoding="utf-8" ?>
    <D:propfind xmlns:D="DAV:">
    <D:prop><D:creationdate/>
    <D:getcontentlength/>
    <D:displayname/>
    <D:source/>
    <D:getcontentlanguage/>
    <D:getcontenttype/>
    <D:getlastmodified/>
    <D:getetag/>
    <D:supportedlock/>
    <D:lockdiscovery/>
    <D:resourcetype/>
    <D:quota-available-bytes/>
    <D:quota-used-bytes/>
    </D:prop>
    </D:propfind>
    Ответ:
    <?xml version="1.0" encoding="utf-8" ?>
  <D:multistatus xmlns:D="DAV:">
    <D:response>
      <D:href>http://www.foo.bar/file</D:href>
      <D:propstat>
        <D:prop xmlns:R="http://www.foo.bar/boxschema/">
          <R:bigbox>
            <R:BoxType>Box type A</R:BoxType>
          </R:bigbox>
          <R:author>
            <R:Name>J.J. Johnson</R:Name>
          </R:author>
        </D:prop>
        <D:status>HTTP/1.1 200 OK</D:status>
      </D:propstat>
      <D:propstat>
        <D:prop>
          <R:DingALing/>
          <R:Random/>
        </D:prop>
        <D:status>HTTP/1.1 403 Forbidden</D:status>
        <D:responsedescription>
          The user does not have access to the DingALing property.
        </D:responsedescription>
      </D:propstat>
    </D:response>
    <D:responsedescription>
      There has been an access violation error.
    </D:responsedescription>
  </D:multistatus>
  
  https://citforum.ru/internet/webservers/webdav/'''
    print('pathname:', pathname)
    print(request.headers)
    print(request.args)
    print(request.data)
    return ''



@bp.route("/webdav/<int:project_id>/<path:pathname>", methods=["PUT"])
def put_file_to_dir(project_id: int, pathname: str):
    project = db.get_or_404(models.Project, project_id)
    pass