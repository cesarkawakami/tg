import gridfs
import pymongo
import uuid

D = pymongo.Connection().main
ProblemsFS = gridfs.GridFS(D, "problems.fs")

# just guarantees some data into db
def init():
    D.hashes.find_and_modify(
        {"object": "runs"},
        {"object": "runs", "hash": str(uuid.uuid4())},
        upsert=True
    )
