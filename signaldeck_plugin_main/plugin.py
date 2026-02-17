from flask import Blueprint

bp = Blueprint(
    "main",                 # blueprint name
    __name__,
    template_folder="templates"  # optional, verhindert static collisions
)

def register(app, ctx=None) -> None:
    """
    Called by signaldeck-core to register this plugin.
    ctx is optional here; blueprint registration doesn't need it.
    """
    app.register_blueprint(bp)
