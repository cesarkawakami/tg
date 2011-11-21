import json
import pika, pika.adapters.tornado_connection
import tornado.ioloop
from tornado import gen
from bson.objectid import ObjectId

import proto
from db import ProblemsFS


@proto.singleton
class ProblemFileReplier(proto.ProblemFileMixin, proto.Replier):
    def handle(self, data, route_data):
        with ProblemsFS.get(ObjectId(data["id"])) as fh:
            blob = fh.read()
        self.respond({"blob": self.encode(blob)}, route_data)


@proto.singleton
class WorkerRequester(proto.WorkerMixin, proto.Requester):
    pass


class ContestantMixin(object):
    EXCHANGE_NAME = "contestant"


@proto.singleton
class ContestantPublisher(ContestantMixin, proto.Publisher):
    pass


class ContestantSubscriber(ContestantMixin, proto.Subscriber):
    def __init__(self, id_, callback):
        self._id = id_
        self._callback = callback

    @gen.engine
    def setup(self, callback):
        yield gen.Task(
            super(ContestantSubscriber, self).setup,
            proto.PikaClient.get().connection,
            self._id
        )
        callback()

    def handle(self, data):
        print "callback"
        self._callback(data)
        self.close()


def setup():
    proto.PikaClient.get().setup(
        clients=[
            ProblemFileReplier.get(),
            WorkerRequester.get(),
            ContestantPublisher.get(),
        ],
        connection_class=pika.adapters.tornado_connection.TornadoConnection
    )
    tornado.ioloop.IOLoop.instance().add_timeout(500, proto.PikaClient.get().connect)
