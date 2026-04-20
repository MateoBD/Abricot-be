from flask import current_app
from flask_restx import Namespace, Resource, fields

namespace = Namespace(
    name="System",
    path="",
    description="Operational endpoints for health and version.",
)

health_model = namespace.model(
    "HealthResponse",
    {
        "status": fields.String(
            description="Service liveness status.",
            example="ok",
        )
    },
)

version_model = namespace.model(
    "VersionResponse",
    {
        "version": fields.String(
            description="API semantic version.",
            example="1.0.0",
        ),
        "gitSha": fields.String(
            description="Deployed git commit SHA.",
            example="unknown",
        ),
    },
)


@namespace.route("/health")
class Health(Resource):
    @namespace.response(200, "Service is healthy.", health_model)
    def get(self):
        """Liveness probe endpoint."""
        return {"status": "ok"}, 200


@namespace.route("/version")
class Version(Resource):
    @namespace.response(200, "Version metadata retrieved.", version_model)
    def get(self):
        """Returns public API version metadata."""
        return {
            "version": current_app.config.get("API_VERSION", "1.0.0"),
            "gitSha": current_app.config.get("GIT_SHA", "unknown"),
        }, 200
