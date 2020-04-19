"""
The add_* return instance whether or not it exists, and should persist
it either way.
The get_* and *.from_path return only existing instances.
"""
import os
from os.path import join, isfile, isdir, exists
from glob import glob
import string
from threading import Lock

from flask import current_app
import git

ext = ".md"
glob_ext = f"*{ext}"
ext_len = len(ext)


# -- path library


def list_subdir_paths_no_trailing_slash(the_dir):
    return [
        join(the_dir, d).rstrip("/")
        for d in os.listdir(the_dir)
        if isdir(join(the_dir, d))
    ]


def list_subdir_names(the_dir):
    return [d for d in os.listdir(the_dir) if isdir(join(the_dir, d))]


# -- errors


class ImSory(ValueError):
    pass


class ImSoryButNo(ImSory):
    pass


def ass(condition, message, no=False):
    if condition:
        return

    if no:
        raise ImSoryButNo(message)

    raise ImSory(message)


# -- model classes


class card:

    chars = string.digits + string.ascii_letters + " "

    def __init__(self, name, column_root):
        assert isdir(column_root)
        assert len(name) <= 61
        self.name = name
        self.column_root = column_root
        self.path = join(column_root, f"{name}{ext}")
        self._validate()

    def _validate(self):
        ass(
            all(c in self.chars for c in self.name),
            f"Invalid name {self.name} for card.",
        )
        ass(
            self.column_root,
            f"Card needs a column root but got {self.column_root}.",
        )
        ass(
            isdir(self.column_root),
            f"Card's column root {self.column_root} not a directory.",
        )
        ass(
            self.path.endswith(ext),
            f"Card path needs to end with {ext} but was {self.path}.",
        )
        if exists(self.path):
            ass(
                isfile(self.path),
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
        ass(isfile(filename), "from_filename but it didn't exist.", no=True)
        return card(name_md[:-ext_len], column_root)


class column:

    chars = string.digits + string.ascii_letters + " "

    def __init__(self, name, board_root):
        assert isdir(board_root)
        self.name = name
        self.board_root = board_root
        self.path = join(board_root, name)
        self._validate()

    def _validate(self):
        ass(
            all(c in self.chars for c in self.name),
            f"{self.name} invalid name for column.",
        )
        ass(self.board_root, f"Column got abd board root {self.board_root}.")
        ass(
            isdir(self.board_root),
            f"Column's board root {self.board_root} was not a directory.",
        )

        # Ensure directory exists
        if exists(self.path):
            ass(
                isdir(self.path),
                f"Column path {self.path} exists but is not a directory.",
            )
        else:
            os.makedirs(self.path)

        # Ensure index exists
        if exists(join(self.path, ".index")):
            ass(isfile(join(self.path, ".index")), "Bad column index.")
        else:
            open(join(self.path, ".index"), "w").close()

    def __contains__(self, other):
        if isinstance(other, card):
            return card in self.cards

    @property
    def cards(self):
        self._validate()
        return [card.from_filename(f) for f in glob(join(self.path, glob_ext))]

    def get_card(self, name):
        return card.from_filename(join(self.path, f"{name}{ext}"))

    def add_card(self, name):
        try:
            return self.get_card(name)
        except ImSoryButNo:
            with commit_txn(f"Column {self.name} add card {name}."):
                k = card(name, self.path)
            return k

    @classmethod
    def from_path(cls, path):
        assert not path.endswith("/")
        ass(isdir(path), "from_path but it didn't exist.", no=True)
        board_root, card_dir = os.path.split(path)
        return cls(card_dir, board_root)


class board:

    chars = string.ascii_lowercase

    def __init__(self, name, root):
        assert exists(root)
        self.name = name
        self.root = root
        self.path = join(root, name)
        self._validate()

    def _validate(self):
        ass(self.root, f"Bad board root {self.root}.")
        ass(
            isdir(self.root), f"Board root {self.root} not a directory.",
        )
        ass(
            all(c in self.chars for c in self.name),
            f"Bad board name {self.name}",
        )

        # Ensure directory exists
        if exists(self.path):
            ass(
                isdir(self.path),
                f"Board path {self.path} exists but is not a directory.",
            )
        else:
            os.makedirs(self.path)

        # Ensure keepfile exists
        if exists(join(self.path, ".keep")):
            ass(isfile(join(self.path, ".keep")), "Bad .keep.")
        else:
            open(join(self.path, ".keep"), "w").close()

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
        try:
            return self.get_column(name)
        except ImSoryButNo:
            with commit_txn(f"Board {self.name} add column {name}"):
                c = column(name, self.path)
            return c

    @classmethod
    def from_path(cls, path):
        assert not path.endswith("/")
        ass(isdir(path), "from_path but it didn't exist.", no=True)
        db_root, board_dir = os.path.split(path)
        return cls(board_dir, db_root)


# -- git layer

lock = Lock()

try:
    repo = git.Repo(current_app.instance_path)
except git.InvalidGitRepositoryError:
    repo = git.Repo.init(current_app.instance_path)


class commit_txn:
    def __init__(self, path, commit_message):
        self.path = path
        self.commit_message = commit_message

    def __enter__(self):
        ass(not repo.index.diff(None), "I don't want to mess with that.")
        lock.acquire()

    def __exit__(self):
        repo.index.add([self.path])
        ass(
            len(repo.index.diff(None)) == 1,
            "Whoah there. One thing at a time.",
        )
        repo.index.commit(self.commit_message)
        lock.release()


# -- global model api


def add_board(name):
    try:
        return get_board(name)
    except ImSoryButNo:
        with commit_txn(f"Add board {name}."):
            b = board(name, current_app.instance_path)
        return b


def get_board(name):
    return board.from_path(join(current_app.instance_path, name))


def _boards():
    return [
        board.from_path(p)
        for p in list_subdir_paths_no_trailing_slash(current_app.instance_path)
    ]


# make this module look like its classes
def __getattr__(name):
    if name == "boards":
        return _boards()
    ass(False, f"Um. You were looking for {name}? I don't know her.")
