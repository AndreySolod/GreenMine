import os


class ImportDefaultData:
    def __init__(self):
        self.is_complex = False

    def data(self, app, cls, db):
        path = os.path.join(app.root_path, 'static', 'js', 'highlight', 'styles')
        obj_list = []
        for current_dir, dirs, files in os.walk(path):
            current_dir = current_dir[len(path)::]
            for f in files:
                if f.endswith(".css"):
                    if current_dir == '':
                        now_item = cls()
                        now_item.string_slug = f.split('.')[0]
                        now_item.title = f.split('.')[0]
                        now_item.directory = current_dir
                        now_item.filename = f
                    else:
                        now_item = cls()
                        now_item.string_slug = current_dir + '-' + f.split('.')[0]
                        now_item.title = current_dir + '-' + f.split('.')[0]
                        now_item.directory = current_dir
                        now_item.filename = f
                    db.session.add(now_item)
                    obj_list.append(now_item)
        if len(obj_list) > 0:
            obj_list[0].is_default = True
            db.session.add(obj_list[0])
        db.session.commit()
