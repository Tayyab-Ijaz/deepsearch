"""Tiny in-memory stand-in for the parts of Firestore the API uses, so tests never touch a real project."""
from types import SimpleNamespace


class Snap:
    def __init__(self, ref, data):
        self.reference, self._data, self.exists = ref, data, data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class Ref:
    def __init__(self, db, collection, doc_id):
        self.db, self.collection, self.id = db, collection, doc_id

    def get(self, transaction=None):
        return Snap(self, self.db.data.get(self.collection, {}).get(self.id))

    def set(self, data):
        self.db.data.setdefault(self.collection, {})[self.id] = dict(data)

    def delete(self):
        self.db.data.get(self.collection, {}).pop(self.id, None)


class Collection:
    def __init__(self, db, name):
        self.db, self.name = db, name

    def document(self, doc_id):
        return Ref(self.db, self.name, doc_id)

    def add(self, data):
        self.db.data.setdefault(self.name, {})[f"auto{len(self.db.data.get(self.name, {}))}"] = dict(data)

    def where(self, field, op, value):
        assert op == "=="
        rows = self.db.data.get(self.name, {})
        return SimpleNamespace(stream=lambda: [Snap(Ref(self.db, self.name, i), d) for i, d in list(rows.items()) if d.get(field) == value])


class Writes:
    def set(self, ref, data):
        ref.set(data)

    def delete(self, ref):
        ref.delete()

    def commit(self):
        pass


class FakeDB:
    def __init__(self):
        self.data = {}

    def collection(self, name):
        return Collection(self, name)

    def transaction(self):
        return Writes()

    def batch(self):
        return Writes()


# `transactional` wraps a function that receives the transaction; here it can simply run directly.
fake_firestore_module = SimpleNamespace(transactional=lambda fn: fn)
