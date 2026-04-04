from project import db


class TemplateModel(db.Model):
    """Database model example"""

    """Defines the table name — change this to match your entity"""
    __tablename__ = "template"

    """Primary key fiel d — can be renamed or changed to another identifier type"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    """Example field — add, remove, or modify according to your model's requirements"""
    some_field = db.Column(db.String(100), nullable=False, unique=False)

    def to_dict(self):
        """Converts the model instance into a dictionary"""

        """Update the returned keys if your API uses different naming conventions"""
        return {"id": self.id, "someField": self.some_field}
