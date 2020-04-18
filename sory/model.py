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


# -- model classes


class card:
    def __init__(self, name, column_root):
        assert os.path.isdir(column_root)
        assert len(name) <= 61
        self.name = name
        self.column_root = column_root
        self.path = join(column_root, f"{name}{ext}")
        self._validate()

    def _validate(self):
        assert all(c in string.ascii_letters for c in self.name)
        assert self.column_root
        assert os.path.isdir(self.column_root)
        assert self.path.endswith(ext)
        if os.path.exists(self.path):
            assert os.path.isfile(self.path)
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
        return card(name_md[:-ext_len])


class column:
    def __init__(self, name, board_root):
        assert os.path.isdir(board_root)
        self.name = name
        self.board_root = board_root
        self.path = join(board_root, name)
        self._validate()

    def _validate(self):
        assert all(c in string.ascii_lowercase for c in self.name)
        assert self.board_root
        assert os.path.isdir(self.board_root)
        if os.path.exists(self.path):
            assert os.path.isdir(self.path)
        else:
            os.makedirs(self.path)

    def __contains__(self, other):
        if isinstance(other, card):
            return card in self.cards

    @property
    def cards(self):
        self._validate()
        return [card.from_file(f) for f in glob(join(self.path, glob_ext))]

    def add_card(self, name):
        return card(name, self.path)

    @classmethod
    def from_path(cls, path):
        assert not path.endswith("/")
        board_root, card_dir = os.path.split(path)
        return cls(card_dir, board_root)


class board:
    def __init__(self, name, root):
        assert os.path.exists(root)
        self.name = name
        self.root = root
        self.path = join(root, name)
        self._validate()

    def _validate(self):
        assert self.root
        assert os.path.isdir(self.root)
        assert all(c in string.ascii_lowercase for c in self.name)
        if os.path.exists(self.path):
            assert os.path.isdir(self.path)
        else:
            os.makedirs(self.path)

    @property
    def columns(self):
        return [
            column.from_path(p)
            for p in list_subdir_paths_no_trailing_slash(self.path)
        ]

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


def boards():
    return [
        board.from_path(p)
        for p in list_subdir_paths_no_trailing_slash(current_app.instance_path)
    ]
