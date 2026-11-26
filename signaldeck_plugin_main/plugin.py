from flask import Blueprint

bp = Blueprint(
    "main",                 # blueprint name
    __name__,
    template_folder="templates",  # optional, verhindert static collisions
    static_folder="static",
    url_prefix="/plugin/main",   # optional: URLs für plugin views/static (views optional)
    static_url_path="/static"
)

def register(app, ctx=None) -> None:
    """
    Called by signaldeck-core to register this plugin.
    ctx is optional here; blueprint registration doesn't need it.
    """
    app.register_blueprint(bp)
    if ctx is not None and getattr(ctx, "publishers", None) is not None:
        from .publishers import HttpPublisher, MqttPublisher
        ctx.publishers.register("http", HttpPublisher)
        ctx.publishers.register("mqtt", MqttPublisher)
