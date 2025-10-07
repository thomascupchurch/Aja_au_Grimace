from project.model import ProjectDataModel

def test_load_and_save_roundtrip(tmp_path):
    m = ProjectDataModel()
    m.DB_FILE = tmp_path / "proj.db"
    m.ensure_schema()
    m.rows = [{
        "Project Part":"Test",
        "Parent":"",
        "% Complete":0,
        "Status":"Planned"
    }]
    m.save_to_db()
    m.rows = []
    m.load_from_db()
    assert any(r.get("Project Part")=="Test" for r in m.rows)