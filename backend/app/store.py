"""Durable optimistic storage. SQLite locally; Firestore on Cloud Run."""
import json
import os
import sqlite3
from pathlib import Path

from .domain import Project


class Conflict(Exception):
    pass


class Store:
    def __init__(self, path=None):
        self.cloud = os.getenv("STORYPARITY_STORE") == "firestore" and path is None
        if self.cloud:
            from google.cloud import firestore
            self.db = firestore.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])
            self.collection = self.db.collection(os.getenv("STORYPARITY_FIRESTORE_COLLECTION", "storyparity_projects"))
        else:
            self.path = Path(path or os.getenv("STORYPARITY_DB", "runtime/storyparity.sqlite"))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.connect() as db:
                db.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def list(self):
        if self.cloud:
            values = [x.to_dict()["body"] for x in self.collection.stream()]
        else:
            with self.connect() as db:
                values = [x[0] for x in db.execute("SELECT body FROM projects ORDER BY rowid DESC")]
        return [{"id": p.id, "title": p.title, "status": p.status, "revision": p.revision} for p in map(Project.model_validate_json, values)]

    def get(self, project_id):
        if self.cloud:
            row = self.collection.document(project_id).get()
            body = row.to_dict()["body"] if row.exists else None
        else:
            with self.connect() as db:
                row = db.execute("SELECT body FROM projects WHERE id=?", (project_id,)).fetchone()
                body = row[0] if row else None
        if body is None:
            raise KeyError(project_id)
        return Project.model_validate_json(body)

    def save(self, project: Project, expected: int | None):
        next_revision = 1 if expected is None else expected + 1
        candidate = project.model_copy(deep=True)
        candidate.revision = next_revision
        body = candidate.model_dump_json()
        # Firestore document limit; explicit failure instead of truncated audit data.
        if self.cloud and len(body.encode()) > 900000:
            raise ValueError("Project exceeds document limit; split delivery into smaller projects")
        if self.cloud:
            from google.cloud import firestore
            ref = self.collection.document(project.id)

            @firestore.transactional
            def commit(transaction):
                current = ref.get(transaction=transaction)
                actual = current.to_dict()["revision"] if current.exists else None
                if actual != expected:
                    raise Conflict("Project changed; reload before retrying")
                transaction.set(ref, {"revision": next_revision, "body": body})
            commit(self.db.transaction())
        else:
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT revision FROM projects WHERE id=?", (project.id,)).fetchone()
                if (row[0] if row else None) != expected:
                    raise Conflict("Project changed; reload before retrying")
                db.execute("INSERT OR REPLACE INTO projects VALUES (?,?,?)", (project.id, next_revision, body))
        project.revision = next_revision


class MediaStore:
    def __init__(self):
        self.bucket = os.getenv("STORYPARITY_MEDIA_BUCKET")
        self.root = Path(os.getenv("STORYPARITY_MEDIA_DIR", "runtime/media"))

    def put(self, key: str, data: bytes, mime: str):
        if self.bucket:
            from google.cloud import storage
            storage.Client().bucket(self.bucket).blob(key).upload_from_string(data, content_type=mime)
        else:
            self.root.mkdir(parents=True, exist_ok=True)
            (self.root / key).write_bytes(data)

    def get(self, key):
        if self.bucket:
            from google.cloud import storage
            return storage.Client().bucket(self.bucket).blob(key).download_as_bytes()
        return (self.root / key).read_bytes()
