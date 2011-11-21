import base64
import json
import os
import pika, pika.adapters
import uuid
from bson.objectid import ObjectId
from tornado import gen


def singleton(cls):
    cls.__instance = None
    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = cls()
        return cls.__instance
    cls.get = get
    return cls


@singleton
class PikaClient(object):
    def setup(self, clients=[], connection_class=pika.adapters.SelectConnection, *args, **kwargs):
        self._clients = clients
        self._connection_class = connection_class
        self._connection_args = args
        self._connection_kwargs = kwargs

    def connect(self):
        self.connection = self._connection_class(
            on_open_callback=self.on_connected,
            *self._connection_args,
            **self._connection_kwargs
        )

    def on_connected(self, connection):
        for client in self._clients:
            result = client.setup(connection)

    def start(self):
        try:
            self.connection.ioloop.start()
        finally:
            self.connection.close()
            self.connection.ioloop.start()


class Requester(object):
    QUEUE_NAME = None # must be overriden in subclasses

    def __init__(self):
        self._callbacks = {}

    @gen.engine
    def setup(self, connection):
        connection.channel((yield gen.Callback("channel")))
        self.channel = yield gen.Wait("channel")
        self.callback_queue = (
            yield gen.Task(self.channel.queue_declare, exclusive=True)
        ).method.queue
        # also declaring target queue
        yield gen.Task(self.channel.queue_declare, queue=self.QUEUE_NAME)
        self.channel.basic_consume(self.on_response, no_ack=True, queue=self.callback_queue)

    def on_response(self, channel, method, headers, body):
        try:
            callback = self._callbacks[headers.correlation_id]
        except KeyError:
            return
        del self._callbacks[headers.correlation_id]
        callback(json.loads(body))

    def request(self, data, callback):
        print
        print
        print
        print
        print
        print "=========== REQUESTING ============="
        import traceback
        traceback.print_stack()
        correlation_id = str(uuid.uuid4())
        self._callbacks[correlation_id] = callback
        self.channel.basic_publish(
            exchange="",
            routing_key=self.QUEUE_NAME,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=correlation_id
            ),
            body=json.dumps(data)
        )


class Replier(object):
    QUEUE_NAME = "" # must be overridden in subclasses

    @gen.engine
    def setup(self, connection):
        connection.channel((yield gen.Callback("channel")))
        self.channel = yield gen.Wait("channel")
        yield gen.Task(self.channel.queue_declare, queue=self.QUEUE_NAME)
        yield gen.Task(self.channel.basic_qos, prefetch_count=1) # fair balancing
        self.channel.basic_consume(self.on_request, queue=self.QUEUE_NAME)

    def on_request(self, channel, method, headers, body):
        print method.delivery_tag
        route_data = {
            "publish": {
                "exchange": "",
                "routing_key": headers.reply_to,
                "properties": pika.BasicProperties(correlation_id=headers.correlation_id),
            },
            "ack": {
                "delivery_tag": method.delivery_tag,
            }
        }
        self.handle(json.loads(body), route_data)

    def handle(self, data, route_data):
        raise NotImplementedError # must be overridden in subclasses

    def respond(self, data, route_data):
        print route_data
        self.channel.basic_publish(body=json.dumps(data), **route_data["publish"])
        self.channel.basic_ack(**route_data["ack"])


class Publisher(object):
    EXCHANGE_NAME = "" # must be overriden in subclasses

    @gen.engine
    def setup(self, connection):
        connection.channel((yield gen.Callback("channel")))
        self.channel = yield gen.Wait("channel")
        yield gen.Task(self.channel.exchange_declare, exchange=self.EXCHANGE_NAME, type="topic")

    def publish(self, data, routing_key):
        self.channel.basic_publish(
            exchange=self.EXCHANGE_NAME,
            routing_key=routing_key,
            body=json.dumps(data)
        )


class Subscriber(object):
    EXCHANGE_NAME = "" # must be overriden in subclasses

    @gen.engine
    def setup(self, connection, routing_key, callback):
        connection.channel((yield gen.Callback("channel")))
        self.channel = yield gen.Wait("channel")
        self.queue = (yield gen.Task(self.channel.queue_declare, exclusive=True)).method.queue
        yield gen.Task(self.channel.queue_bind,
            exchange=self.EXCHANGE_NAME,
            queue=self.queue,
            routing_key=routing_key
        )
        self.channel.basic_consume(self.on_message, queue=self.queue, no_ack=True)
        callback()

    def on_message(self, channel, method, headers, data):
        self.handle(json.loads(data))

    def handle(self, data):
        raise NotImplementedError

    def close(self):
        self.channel.queue_delete(queue=self.queue)


class ProblemFileMixin(object):
    QUEUE_NAME = "problem_file"

    def encode(self, blob):
        return base64.b64encode(blob)

    def decode(self, text):
        return base64.b64decode(text)


class WorkerMixin(object):
    QUEUE_NAME = "worker"


