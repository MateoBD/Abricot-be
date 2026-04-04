import logging

from flask import request
from flask_restx import Namespace, Resource
from werkzeug.exceptions import BadRequest

from project.blueprints.models.template_model import template_model
from project.blueprints.models.template_response_model import (
    template_response_model,
)
from project.helpers.authentication import require_authentication
from project.repositories.template_repository import TemplateRepository

logger = logging.getLogger(__name__)

namespace = Namespace(
    name="Template endpoint",
    path="/endpoints",
    description="Template endpoints",
    decorators=[require_authentication()],
)

namespace.models[template_model.name] = template_model
namespace.models[template_response_model.name] = template_response_model

@namespace.route("/")
class TemplateEndpoint(Resource):
    @namespace.expect(template_model, validate=True)
    @namespace.response(200, "Template success response", [template_response_model])
    def post(self):
        if not request.json:
            logger.error("No input data provided")
            return BadRequest("No input data provided")
        data = request.json
        """
        if some_condition:
            raise TemplateException(f"Some error message.", {"Some field": "Some value"})
        """
        id = TemplateRepository.add(data)
        return {"id": id}, 201

    @namespace.doc(params={"someParam": {"description": "Some filter parameter"}})
    @namespace.response(
        200, "Templates retrieved successfully", [template_response_model]
    )
    def get(self):
        filter_value = request.args.get("filterValue")
        rows = TemplateRepository.get_filtered(filter_value)
        return [row.to_dict() for row in rows], 200
