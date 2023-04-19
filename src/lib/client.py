import socket
import time
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ClientRDT")

class ClientRDT:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        logger.info("Client RDT running")
        # create a socket with udp protocol
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logger.info("Client connecting to: {}:{}".format(str(self.host), str(self.port)))

        # try to connect to the server if not return exception
        try:
            sock.connect((self.host, self.port))
        except Exception as e:
            logger.error("Error: " + str(e))
            # create new exception
            raise Exception("Error connecting to server: {}:{}".format(str(self.host), str(self.port)))
        
        logger.info("Client connected to: {}:{}".format(str(self.host), str(self.port)))
        self.sock = sock

    def send(self, data):
        if self.sock is None:
            clientNotConnectedError = "Client not connected to server"
            logger.error(clientNotConnectedError)
            raise Exception(clientNotConnectedError)
        # sending numbers increasing by 1
        while True:
            time.sleep(1)
            data = data + 1
            logger.info("Sending: " + str(data))
            self.sock.send(str(data).encode("utf-8"))
            # print received message
            logger.info("Received: " + self.sock.recv(1024).decode("utf-8"))