from flask import Blueprint, render_template, request, jsonify
import subprocess
from .admin import check_management_password, check_password

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/admin-auth", methods=["POST"])
def admin_auth():
    data = request.get_json() or {}
    pw = data.get("password", "")

    if check_management_password(pw):
        return jsonify({"ok": True})

    return jsonify({"ok": False, "message": "Sai mat khau!"}), 401

@main.route("/exit", methods=["POST"])
def exit_kiosk():
    data = request.get_json() or {}
    pw = data.get("password", "")

    if check_password(pw):
        try:
            subprocess.run(["pkill", "firefox"])
            return jsonify ({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})

    return jsonify({"ok": False, "message": "sai mau khau!"})
