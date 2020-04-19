from flask import (
    Blueprint,
    redirect,
    request,
    url_for,
    render_template,  # flash, g, ,
)
from . import model

bp = Blueprint("boards", __name__)


@bp.route("/create", methods=("POST",))
def create():
    errors = []

    name = request.form.get("name")
    if name:
        try:
            board = model.get_board(name)
            print("added", name)
            return redirect(url_for("sory", board=board.name), code=303)
        except ValueError as e:
            errors.append(str(e))
    else:
        errors.append("No name submitted with form?")

    return render_template(
        "sory/sory.html", boards=model.boards, board=None, errors=errors
    )
