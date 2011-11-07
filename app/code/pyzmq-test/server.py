import zmq

context = zmq.Context()

socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:10302")

print "Press enter when ready..."
raw_input()
print "Dispatching 100 requests."

replies = {}

for request in xrange(0, 100):
    socket.send(str(request))
    reply = socket.recv()
    replies[request] = reply
    print ".",

for reply in replies:
    print reply, replies[reply]
