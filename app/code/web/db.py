import gridfs
import pymongo

D = pymongo.Connection().main
ProblemsFS = gridfs.GridFS(D, "problems.fs")
