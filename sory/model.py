"""
The add_* return instance whether or not it exists, and should persist
it either way.
The get_* and *.from_path return only existing instances.
"""
import os
from os.path import join
from glob import glob
import string
from flask import current_app

ext = ".md"
glob_ext = f"*{ext}"
ext_len = len(ext)


# -- path library


def list_subdir_paths_no_trailing_slash(the_dir):
    return [
        join(the_dir, d).rstrip("/")
        for d in os.listdir(the_dir)
        if os.path.isdir(join(the_dir, d))
    ]


def list_subdir_names(the_dir):
    return [d for d in os.listdir(the_dir) if os.path.isdir(join(the_dir, d))]


# -- error


class ImSory(ValueError):
    pass


def err(condition, message):
    if not condition:
        raise ImSory(message)


# -- model classes


class card:

    chars = string.digits + string.ascii_letters + ' '

    def __init__(self, name, column_root):
        assert os.path.isdir(column_root)
        assert len(name) <= 61
        self.name = name
        self.column_root = column_root
        self.path = join(column_root, f"{name}{ext}")
        self._validate()

    def _validate(self):
        err(
            all(c in self.chars for c in self.name),
            f"Invalid name {self.name} for card.",
        )
        err(
            self.column_root,
            f"Card needs a column root but got {self.column_root}.",
        )
        err(
            os.path.isdir(self.column_root),
            f"Card's column root {self.column_root} not a directory.",
        )
        err(
            self.path.endswith(ext),
            f"Card path needs to end with {ext} but was {self.path}.",
        )
        if os.path.exists(self.path):
            err(
                os.path.isfile(self.path),
                f"Card path {self.path} already existed but was not a file.",
            )
        else:
            open(self.path, "w").close()

    def __eq__(self, other):
        return isinstance(other, card) and other.path == self.path

    @property
    def content(self):
        self._validate()
        with open(self.path, "r") as card_md:
            content = card_md.read()
        return content

    @classmethod
    def from_filename(cls, filename):
        column_root, name_md = os.path.split(filename)
        assert column_root
        assert name_md.endswith(ext)
        return card(name_md[:-ext_len], column_root)


class column:

    chars = string.digits + string.ascii_letters + ' '

    def __init__(self, name, board_root):
        assert os.path.isdir(board_root)
        self.name = name
        self.board_root = board_root
        self.path = join(board_root, name)
        self._validate()

    def _validate(self):
        err(
            all(c in self.chars for c in self.name),
            f"{self.name} invalid name for column.",
        )
        err(self.board_root, f"Column got abd board root {self.board_root}.")
        err(
            os.path.isdir(self.board_root),
            f"Column's board root {self.board_root} was not a directory.",
        )
        if os.path.exists(self.path):
            err(
                os.path.isdir(self.path),
                f"Column path {self.path} exists but is not a directory.",
            )
        else:
            os.makedirs(self.path)

    def __contains__(self, other):
        if isinstance(other, card):
            return card in self.cards

    @property
    def cards(self):
        self._validate()
        return [card.from_filename(f) for f in glob(join(self.path, glob_ext))]

    def add_card(self, name):
        return card(name, self.path)

    @classmethod
    def from_path(cls, path):
        assert not path.endswith("/")
        board_root, card_dir = os.path.split(path)
        return cls(card_dir, board_root)


class board:

    chars = string.ascii_lowercase

    def __init__(self, name, root):
        assert os.path.exists(root)
        self.name = name
        self.root = root
        self.path = join(root, name)
        self._validate()

    def _validate(self):
        err(self.root, f"Bad board root {self.root}.")
        err(
            os.path.isdir(self.root),
            f"Board root {self.root} not a directory.",
        )
        err(
            all(c in self.chars for c in self.name),
            f"Bad board name {self.name}",
        )
        if os.path.exists(self.path):
            err(
                os.path.isdir(self.path),
                f"Board path {self.path} exists but is not a directory.",
            )
        else:
            os.makedirs(self.path)

    def __eq__(self, other):
        return isinstance(other, board) and self.path == other.path

    @property
    def columns(self):
        return [
            column.from_path(p)
            for p in list_subdir_paths_no_trailing_slash(self.path)
        ]

    def get_column(self, name):
        return column.from_path(join(self.path, name))

    def add_column(self, name):
        return column(name, self.path)

    @classmethod
    def from_path(cls, path):
        assert not path.endswith("/")
        db_root, board_dir = os.path.split(path)
        return cls(board_dir, db_root)


# -- global model api


def add_board(name):
    return board(name, current_app.instance_path)


def get_board(name):
    return board.from_path(join(current_app.instance_path, name))


def _boards():
    return [
        board.from_path(p)
        for p in list_subdir_paths_no_trailing_slash(current_app.instance_path)
    ]


# make this module look like the other classes
def __getattr__(name):
    if name == "boards":
        return _boards()
    err(False, f"Um. You were looking for {name}? I don't know her.")
