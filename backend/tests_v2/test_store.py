import pytest

from backend.app.store import Conflict, Store
from .fixtures import make_project


def test_project_and_audit_survive_new_store_instance(tmp_path):
    path = tmp_path / "projects.sqlite"
    project = make_project()
    Store(path).save(project, expected=None)
    recovered = Store(path).get(project.id)
    assert recovered.model_dump() == project.model_dump()
    assert recovered.events[0].action == "SYNTHETIC_FIXTURE_CREATED"
    assert Store(path).list() == [{"id": project.id, "title": project.title, "status": "INGESTED", "revision": 1}]


def test_concurrent_editor_cannot_overwrite_newer_revision(tmp_path):
    store = Store(tmp_path / "projects.sqlite")
    project = make_project()
    store.save(project, expected=None)
    first, stale = store.get(project.id), store.get(project.id)
    first.title = "First editor saved"
    store.save(first, expected=1)
    stale.title = "Stale editor"
    with pytest.raises(Conflict, match="changed"):
        store.save(stale, expected=1)
    assert stale.revision == 1
    assert store.get(project.id).title == "First editor saved"
    assert store.get(project.id).revision == 2


def test_duplicate_create_and_missing_update_are_rejected(tmp_path):
    store = Store(tmp_path / "projects.sqlite")
    project = make_project()
    with pytest.raises(Conflict):
        store.save(project, expected=1)
    with pytest.raises(KeyError):
        store.get(project.id)
    store.save(project, expected=None)
    with pytest.raises(Conflict):
        store.save(project, expected=None)
    assert store.get(project.id).revision == 1
