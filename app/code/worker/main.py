import zmq

context = zmq.Context()

socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:10301")

socket.send("4eb89f9bcb48ba1264000000")
print "succesfully received", len(socket.recv())/1024/1024, "MB"
