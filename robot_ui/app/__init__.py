from pathlib import Path
from flask import Flask

def create_app():
    root_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(root_dir / "templates"),
        static_folder=str(root_dir / "static"),
    )

    from .routes import main
    app.register_blueprint(main)

    return app
