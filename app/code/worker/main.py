import json
import zmq, zmq.eventloop, zmq.eventloop.zmqstream
from bson.objectid import ObjectId


context = zmq.Context()


class JudgingReplier(object):
    __instance = None

    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = JudgingReplier()
        return cls.__instance

    def setup(self, socket):
        self._stream = zmq.eventloop.zmqstream.ZMQStream(socket, zmq.eventloop.IOLoop.instance())
        self._stream.on_recv(self.handle)

    def handle(self, msg):
        pass


class ProblemFileRequester(object):
    __instance = None

    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = ProblemFileRequester()
        return cls.__instance

    def setup(self, socket):
        self._stream = zmq.eventloop.zmqstream.ZMQStream(socket, zmq.eventloop.IOLoop.instance())

    def request(self, id_, callback):
        import sys
        def on_recv(msg):
            self._stream.stop_on_recv()
            callback(msg[0])
            print "received"
        def on_send(*_):
            self._stream.on_recv(on_recv)
            print "sent"
        self._stream.send(str(id_), callback=on_send)
        print "scheduled"


if __name__ == "__main__":
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://127.0.0.1:10301")
    ProblemFileRequester.get().setup(socket)

    socket = context.socket(zmq.REP)
    socket.connect("tcp://127.0.0.1:10302")
    JudgingReplier.get().setup(socket)

    for i in xrange(10):
        def on_recv(buf):
            print "{0:05d}: successfully received {1} MB".format(i, len(buf)/1024/1024)
        ProblemFileRequester.get().request("4eb89f9bcb48ba1264000000", on_recv)

    zmq.eventloop.IOLoop.instance().start()
