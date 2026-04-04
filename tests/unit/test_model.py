from project.models import TemplateModel


def test_model_creation(_db):
    # Uses the `_db` fixture to get a clean, in-memory SQLite database per test.
    SOME_FIELD_VALUE = "Test Field"

    model = TemplateModel(some_field=SOME_FIELD_VALUE)
    _db.session.add(model)
    _db.session.commit()

    assert model.some_field == SOME_FIELD_VALUE
    assert model.id
