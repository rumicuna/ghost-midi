import socket
import select
import sys
from signal import signal, SIGINT
import argparse
import mido
import binascii
from mido.ports import MultiPort
from mido import sockets
from mido import MidiFile, Message, tempo2bpm

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    arg = parser.add_argument

    arg('host',
        metavar='HOST',
        help='host to connect to')

    arg('port',
        metavar='PORT',
        help='port to connect to')

    arg('midi_ports',
        metavar='MIDI_PORT',
        nargs='+',
        help='input midi ports to listen to')

    return parser.parse_args()

def handler(signal_received, frame):
    # Handle any cleanup here
    print('SIGINT or CTRL-C detected. Exiting gracefully')
    exit(0)

signal(SIGINT, handler)

def prompt():
    sys.stdout.write("> ")
    sys.stdout.flush()


class Client(object):

    def __init__(self):
        self.args = parse_args()
        self.host = self.args.host
        self.port = int(self.args.port)
        if self.args.midi_ports[0] is not '':
            self.midi_ports = [mido.open_input(name) for name in self.args.midi_ports]
            self.midi_ports_out = MultiPort ([mido.open_output(name) for name in self.args.midi_ports])
        else:
            self.midi_ports = None
        self.sock = None
        self.connect_to_server()
            
    def connect_to_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.sock.settimeout(2)
        # connect to remote host
        try:
            self.sock.connect((self.host, self.port))
        except:
            print('Unable to connect')
            sys.exit()

        print('Connected to remote host. Start sending messages')
        prompt()
        self.wait_for_messages()

    def wait_for_messages(self):
        while 1:
            socket_list = [self.sock]

            # Get the list sockets which are readable
            read_sockets, write_sockets, error_sockets = select.select(socket_list, [], [], 0)
            for sock in read_sockets:
                # incoming message from remote server
                if sock == self.sock:
                    data = sock.recv(4096)
                    if not data:
                        print('\nDisconnected from chat server')
                        sys.exit()
                    else:
                        # print data
                        #sys.stdout.write(">" +  str(binascii.unhexlify(data.decode())) + "<")
                        #print("Received1: " + data.decode())
                        messages = str(data.decode()).split("m")
                        if len(messages) >= 2:
                            messages.pop(0)
                            for message in messages:
                                message_header = message[:1]
                                message_body = message[2:]
                                print(message)
                                if message_header == "n":   
                                    notes_hex = message_body
                                    notes_bin = bytearray.fromhex(notes_hex)
                                    notes_mido = mido.parse_all(notes_bin)
                                    print(notes_mido)
                                    if self.midi_ports != None:
                                        for note in notes_mido:
                                            if isinstance(note, Message):
                                                self.midi_ports_out.send(note)
                                            elif note.type == 'set_tempo':
                                                print('Tempo changed to {:.1f} BPM.'.format(
                                                    tempo2bpm(note.tempo)))

            if self.midi_ports != None:
                msg = ''
                bytes = bytearray()
                for message in mido.ports.multi_receive(self.midi_ports, block=False):
                    print('Sending: {}'.format(message))
                    bytes = bytes + message.bin()
                if bytes != b'':
                    message = "mn=" + bytes.hex()
                    #hex = "mn=803c00"
                    #hex = "mn=803c00mn=903740"
                    print("Sent: " + message)
                    self.sock.send(message.encode())
                    #self.sock.send((str(message)).encode())
                    #self.sock.send(message.bin())
            #mido.ports.sleep()


if __name__ == '__main__':
    client = Client()
