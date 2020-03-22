# Tcp Chat server

import socket, select
from signal import signal, SIGINT
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    arg = parser.add_argument

    arg('port',
        metavar='PORT',
        help='port to connect to')

    return parser.parse_args()

def handler(signal_received, frame):
    # Handle any cleanup here
    print('SIGINT or CTRL-C detected. Exiting gracefully')
    exit(0)

signal(SIGINT, handler)

do_extra_chatty_stuff = False

class Server(object):
    # List to keep track of socket descriptors
    CONNECTION_LIST = []
    RECV_BUFFER = 4096  # Advisable to keep it as an exponent of 2

    def __init__(self):
        self.args = parse_args()
        self.port = int(self.args.port)
        self.user_name_dict = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_up_connections()
        self.client_connect()

    def set_up_connections(self):
        # this has no effect, why ?
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))
        self.server_socket.listen(10)  # max simultaneous connections.

        # Add server socket to the list of readable connections
        self.CONNECTION_LIST.append(self.server_socket)

    # Function to broadcast chat messages to all connected clients
    def broadcast_data(self, sock, message):
        # Do not send the message to master socket and the client who has send us the message
        for socket in self.CONNECTION_LIST:
            if socket != self.server_socket and socket != sock:
                # if not send_to_self and sock == socket: return
                try:
                    socket.send(message.encode())
                except:
                    # broken socket connection may be, chat client pressed ctrl+c for example
                    self.clean_socket(socket)

    def send_data_to(self, sock, message):
        try:
            sock.send(message.encode())
        except:
            # broken socket connection may be, chat client pressed ctrl+c for example
            self.clean_socket(sock)

    def clean_socket(self, sock):
        if sock in self.CONNECTION_LIST:
            self.CONNECTION_LIST.remove(sock)
        if sock in self.user_name_dict:
            del self.user_name_dict[sock]
        sock.close()

    def client_connect(self):
        print("Chat server started on port " + str(self.port))
        while 1:
            # Get the list sockets which are ready to be read through select
            read_sockets, write_sockets, error_sockets = select.select(self.CONNECTION_LIST, [], [])

            for sock in read_sockets:
                # New connection
                if sock == self.server_socket:
                    # Handle the case in which there is a new connection recieved through server_socket
                    self.setup_connection()
                # Some incoming message from a client
                else:
                    # Data recieved from client, process it
                    try:
                        # In Windows, sometimes when a TCP program closes abruptly,
                        # a "Connection reset by peer" exception will be thrown
                        data = sock.recv(self.RECV_BUFFER)
                        if data:
                            if do_extra_chatty_stuff:
                                if self.user_name_dict[sock].username is None:
                                    self.set_client_user_name(data, sock)
                                else:
                                    self.broadcast_data(sock, "\r" + '<' + self.user_name_dict[sock].username + '> ' + data.decode())
                            else:
                                self.broadcast_data(sock, data.decode())

                    except:
                        if do_extra_chatty_stuff:
                            self.broadcast_data(sock, "Client (%s) is offline" % self.user_name_dict[sock].username)
                            print("Client (%s) is offline" % self.user_name_dict[sock].username)
                        else:
                            print("Client disconnected")
                            self.clean_socket(sock)
                        continue

        self.server_socket.close()

    def set_client_user_name(self, data, sock):
        self.user_name_dict[sock].username = data.decode().strip()
        print(data.decode().strip() + ', joined the chat room')        
        if do_extra_chatty_stuff:
            self.send_data_to(sock, str(data.decode().strip() + ', you are now in the chat room\n'))
            self.send_data_to_all_regesterd_clents(sock, str(data.decode().strip() + ', has joined the cat room\n'))

    def setup_connection(self):
        sockfd, addr = self.server_socket.accept()
        self.CONNECTION_LIST.append(sockfd)
        print("Client (%s, %s) connected" % addr)
        if do_extra_chatty_stuff:
            self.send_data_to(sockfd, "please enter a username: ")
        self.user_name_dict.update({sockfd: Connection(addr)})

    def send_data_to_all_regesterd_clents(self, sock, message):
        for local_soc, connection in self.user_name_dict.items():
            if local_soc != sock and connection.username is not None:
                self.send_data_to(local_soc, message)


class Connection(object):
    def __init__(self, address):
        self.address = address
        self.username = None


if __name__ == "__main__":
    server = Server()
