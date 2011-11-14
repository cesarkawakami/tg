import json
import pika, pika.adapters.tornado_connection
import tornado.ioloop
from tornado import gen
from bson.objectid import ObjectId

from db import ProblemsFS


connection = None


class PikaClient(object):
    __instance = None

    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = PikaClient()
        return cls.__instance

    def setup(self, clients=[]):
        self._clients = clients

    def connect(self):
        self.connection = pika.adapters.tornado_connection.TornadoConnection(
            on_open_callback=self.on_connected
        )
        self.connection.set_backpressure_multiplier(1000)

    def on_connected(self, connection):
        for client in self._clients:
            client.setup(connection)


class ProblemFileReplier(object):
    QUEUE_NAME = "problem_file"

    __instance = None

    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = ProblemFileReplier()
        return cls.__instance

    @gen.engine
    def setup(self, connection):
        connection.channel((yield gen.Callback("channel")))
        channel = yield gen.Wait("channel")
        yield gen.Task(channel.queue_declare, queue=self.QUEUE_NAME)
        yield gen.Task(channel.basic_qos, prefetch_count=1)
        channel.basic_consume(self.handle, queue=self.QUEUE_NAME)

    def handle(self, channel, method, headers, body):
        with ProblemsFS.get(ObjectId(body)) as fh:
            contents = fh.read()
        channel.basic_publish(
            exchange="",
            routing_key=headers.reply_to,
            properties=pika.BasicProperties(correlation_id=headers.correlation_id),
            body=contents
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)


class JudgingRequester(object):
    QUEUE_NAME = "judging"

    __instance = None

    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = JudgingRequester()
        return cls.__instance

    def __init__(self):
        self._callbacks = {}

    @gen.engine
    def setup(self, connection):
        connection.channel((yield gen.Callback("channel")))
        self.channel = yield gen.Wait("channel")
        self.callback_queue = (
            yield gen.Task(self.channel.queue_declare, exclusive=True)
        ).method.queue
        self.channel.basic_consume(self.on_response, no_ack=True, queue=self.callback_queue)

    def on_response(self, channel, method, headers, body):
        try:
            callback = self._callbacks[headers.correlation_id]
            del self._callbacks[headers.correlation_id]
            callback(json.loads(body))
        except KeyError:
            pass

    def submit(self, data, callback):
        correlation_id = data["id"]
        if self._callbacks.has_key(correlation_id):
            import sys
            sys.exit(1)
        self._callbacks[correlation_id] = callback
        self.channel.basic_publish(
            exchange="",
            routing_key=self.QUEUE_NAME,
            properties=pika.BasicProperties(
                correlation_id=correlation_id,
                reply_to=self.callback_queue
            ),
            body=json.dumps(data)
        )


def _on_connected():
    pass


def setup():
    PikaClient.get().setup([
        ProblemFileReplier.get(),
        JudgingRequester.get(),
    ])
    tornado.ioloop.IOLoop.instance().add_timeout(500, PikaClient.get().connect)
