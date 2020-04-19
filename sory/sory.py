from flask import (
    Blueprint,
    render_template,
    request,  # flash, g, redirect, url_for
)
from . import model

bp = Blueprint("sory", __name__)


@bp.route("/", methods=("GET",))
def sory():
    board = None
    errors = []

    board_name = request.args.get("board")
    if board_name:
        try:
            board = model.get_board(board_name)
        except ValueError as e:
            errors.append(str(e))

    return render_template(
        "sory/sory.html", boards=model.boards, board=board, errors=errors
    )
