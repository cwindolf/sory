from flask import (
    Blueprint,
    render_template,
    request,  # flash, g, redirect, url_for
)
from . import model

bp = Blueprint("boards", __name__)


@bp.route("/create", methods=("POST",))
def create():
    errors = []

    if request.form:
        name = request.form.get("name")
        if name:
            model.add_board(name)
            print("added", name)
        else:
            errors.append("No name submitted with form?")
    else:
        errors.append("No form data when creating board?")

    boards = model.boards()

    return render_template(
        "sory/sory.html", boards=boards, message="fix it", errors=errors
    )
