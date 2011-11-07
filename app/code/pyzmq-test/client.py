import zmq

context = zmq.Context()

socket = context.socket(zmq.REP)
socket.connect("tcp://localhost:10301")

count = 0
while True:
    request = socket.recv()
    socket.send(str(2 * int(request)))
    count += 1
    print count
