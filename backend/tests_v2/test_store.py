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

def test_project_list_uses_creation_time_not_storage_order(tmp_path):
    from backend.app.domain import uid
    store=Store(tmp_path/'ordered.sqlite')
    newer=make_project();newer.created_at='2026-09-08T18:00:00+00:00'
    older=make_project();older.id=uid();older.created_at='2026-09-07T18:00:00+00:00'
    store.save(newer,None);store.save(older,None)
    assert [p['id'] for p in store.list()]==[newer.id,older.id]


def test_expired_firestore_transaction_is_replaced_not_reused():
    from google.api_core.exceptions import InvalidArgument
    from backend.app.store import commit_with_fresh_transaction
    seen=[]
    def commit(transaction):
        seen.append(transaction)
        if len(seen)<3:
            raise InvalidArgument("The referenced transaction has expired or is no longer valid.")
        return "saved"
    assert commit_with_fresh_transaction(commit,object)=="saved"
    assert len({id(t) for t in seen})==3


@pytest.mark.parametrize('error',[Conflict('newer revision'),ValueError('bad data')])
def test_transaction_retry_does_not_hide_revision_or_validation_failure(error):
    from backend.app.store import commit_with_fresh_transaction
    calls=[]
    def commit(transaction):
        calls.append(transaction)
        raise error
    with pytest.raises(type(error)):
        commit_with_fresh_transaction(commit,object)
    assert len(calls)==1
