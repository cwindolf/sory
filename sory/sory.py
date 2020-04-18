from flask import (
    Blueprint,
    render_template,
    # request,  # flash, g, redirect, url_for
)
from . import model

bp = Blueprint("sory", __name__)


@bp.route("/", methods=("GET",))
def index():
    boards = model.boards()
    print(boards)

    return render_template("sory/sory.html", boards=boards, message="fix it")
