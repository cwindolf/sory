from flask import (
    Blueprint,
    render_template,
    request,  # flash, g, redirect, url_for
)
from . import model

bp = Blueprint("sory", __name__)


@bp.route("/", methods=("GET",))
def index():
    board = model.get_board(request.args.get("board"))
    return render_template(
        "sory/sory.html", boards=model.boards, board=board, message="fix it"
    )
