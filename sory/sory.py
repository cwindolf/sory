from flask import (
    Blueprint, render_template,  # flash, g, redirect, request, url_for
)

bp = Blueprint("sory", __name__)


@bp.route("/")
def index():
    return render_template("sory/sory.html", message="fix it")
