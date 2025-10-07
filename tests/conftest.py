# Ensure tests import from package not raw main.py
import pytest
from project import ProjectDataModel

@pytest.fixture(scope="function")
def model_tmp(tmp_path):
    m = ProjectDataModel()
    m.DB_FILE = str(tmp_path / "test.db")
    m.ensure_schema()
    return m