"""아쿠아클레임 웹 앱 (Flask)."""

from __future__ import annotations

from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 증빙 첨부 합계 20MB + 여유
    app.config["JSON_AS_ASCII"] = False
    app.json.ensure_ascii = False

    from .routes import bp
    app.register_blueprint(bp)
    return app
