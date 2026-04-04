from flask_restx import Model, fields

template_model = Model(
    "Template Model",
    {
        "someField": fields.String(
            required=True,
            description="Some field required for the request.",
            example="My System",
        )
    },
)
