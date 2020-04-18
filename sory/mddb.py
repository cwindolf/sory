import os
import string
from flask import current_app


class mddb:
    def __init__(self, name, root):
        self.name = name
        self.root = root
        self.path = os.path.join(root, name)
        os.makedirs(self.path, exist_ok=True)


def add_db(name):
    assert all(c in string.ascii_lowercase for c in name)
    os.makedirs(os.path.join(current_app.instance_path, name), exist_ok=True)


def list_dbs():
    return [
        d
        for d in os.listdir(current_app.instance_path)
        if os.path.isdir(os.path.join(current_app.instance_path, d))
    ]
