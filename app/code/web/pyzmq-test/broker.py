import zmq

pd = zmq.devices.ProcessDevice(zmq.QUEUE, zmq.DEALER, zmq.ROUTER)
pd.bind_in("tcp://localhost:10301")
pd.bind_out("tcp://localhost:10302")
pd.start()
pd.join()
