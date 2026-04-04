from flask_restx import Model, fields

template_response_model = Model(
    "Template Response Model",
    {
        "someField": fields.String(
            required=True,
            description="Some field required for the request.",
            example="My System",
        )
    },
)
