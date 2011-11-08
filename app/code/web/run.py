import zmq, zmq.eventloop, zmq.eventloop.zmqstream
from bson.objectid import ObjectId

from db import ProblemsFS


class ProblemReplier(object):
    def __init__(self, socket):
        self._stream = zmq.eventloop.zmqstream.ZMQStream(socket, zmq.eventloop.IOLoop.instance())
        self._stream.on_recv(self.handle)

    def handle(self, msg):
        with ProblemsFS.get(ObjectId(msg[0])) as fh:
            self._stream.send(fh.read())


def setup():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:10301")
    ProblemReplier(socket)
