from project import db
from project.models.template_model import TemplateModel

"""Repository class to handle TemplateModel database operations"""


class TemplateRepository:
    @classmethod
    def add(cls, data):
        row = TemplateModel(some_field=data.someField)
        db.session.add(row)
        db.session.commit()
        return row.id

    @classmethod
    def get_filtered(cls, filter_value):
        return TemplateModel.query.filter_by(some_field=filter_value).all()
