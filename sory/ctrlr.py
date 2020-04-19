from flask import (
    Blueprint,
    redirect,
    request,
    url_for,
    render_template,  # flash, g, ,
)
from . import model


POST = ("POST",)
bp = Blueprint("ctrlr", __name__)


# -- boards controller


@bp.route("/boards/create", methods=POST)
def create_board():
    board = None
    errors = []

    name = request.form.get("name")
    if name:
        try:
            board = model.add_board(name)
            return redirect(url_for("sory", board=board.name), code=303)
        except ValueError as e:
            errors.append(str(e))
    else:
        errors.append("No name submitted for board add?")

    return render_template(
        "sory/sory.html", boards=model.boards, board=board, errors=errors
    )


# -- column controller


@bp.route("/board/<board_name>/create", methods=POST)
def create_column(board_name):
    board = None
    errors = []

    try:
        board = model.get_board(board_name)
    except ValueError as e:
        errors.append(str(e))

    name = request.form.get("name")
    if board and name:
        try:
            board.add_column(name)
        except ValueError as e:
            errors.append(str(e))
    else:
        errors.append("No name submitted for column add?")

    return render_template(
        "sory/sory.html", boards=model.boards, board=board, errors=errors
    )


# -- card controller


@bp.route("/board/<board_name>/column/<column_name>/create", methods=POST)
def create_card(board_name, column_name):
    board = None
    column = None
    errors = []

    try:
        board = model.get_board(board_name)
    except ValueError as e:
        errors.append(str(e))

    try:
        column = board.get_column(column_name)
    except ValueError as e:
        errors.append(str(e))

    name = request.form.get("name")
    if column and name:
        try:
            column.add_card(name)
        except ValueError as e:
            errors.append(str(e))
    else:
        errors.append("No name submitted for card add?")

    return render_template(
        "sory/sory.html", boards=model.boards, board=board, errors=errors
    )
