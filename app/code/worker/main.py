import json
import os
import pika, pika.adapters
import uuid
from bson.objectid import ObjectId
from tornado import gen

ROOT_TMP_DIR = ""
SRC_DIR = os.path.join(ROOT_TMP_DIR, "src")
BIN_DIR = os.path.join(ROOT_TMP_DIR, "bin")
BOX_DIR = os.path.join(ROOT_TMP_DIR, "box")


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
        self.connection = pika.adapters.SelectConnection(
            on_open_callback=self.on_connected
        )
        # self.connection.set_backpressure_multiplier(1000)

    def on_connected(self, connection):
        for client in self._clients:
            client.setup(connection)

    def start(self):
        try:
            self.connection.ioloop.start()
        finally:
            self.connection.close()
            self.connection.ioloop.start()


class ProblemFileRequester(object):
    QUEUE_NAME="problem_file"

    __instance = None

    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = ProblemFileRequester()
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

    def submit(self, id_, callback):
        correlation_id = str(uuid.uuid4())
        self._callbacks[correlation_id] = callback
        self.channel.basic_publish(
            exchange="",
            routing_key="problem_file",
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=correlation_id
            ),
            body=str(id_)
        )


class JudgingReplier(object):
    QUEUE_NAME="judging"

    __instance = None

    @classmethod
    def get(cls):
        if not cls.__instance:
            cls.__instance = JudgingReplier()
        return cls.__instance

    @gen.engine
    def setup(self, connection):
        connection.channel((yield gen.Callback("channel")))
        channel = yield gen.Wait("channel")
        result = yield gen.Task(channel.queue_declare, queue=self.QUEUE_NAME)
        yield gen.Task(channel.basic_qos, prefetch_count=1)
        channel.basic_consume(self.handle, queue=self.QUEUE_NAME)

    def handle(self, channel, method, headers, body):
        print "received task"
        import time
        time.sleep(0.1)
        channel.basic_publish(
            exchange="",
            routing_key=headers.reply_to,
            properties=pika.BasicProperties(correlation_id=headers.correlation_id),
            body=json.dumps({"status": "OK"})
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
        print "submitted task"


if __name__ == "__main__":
    PikaClient.get().setup([
        ProblemFileRequester.get(),
        JudgingReplier.get(),
    ])
    PikaClient.get().connect()
    PikaClient.get().start()

