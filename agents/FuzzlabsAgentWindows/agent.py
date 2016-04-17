#!/usr/bin/env python

from anyjson import loads, dumps
from socket import socket, timeout, AF_INET, SOCK_STREAM
from thread import start_new_thread
from traceback import print_exc

try:
    import winappdbg
except Exception:
    print "WinAppDbg is not installed, run the following command:"
    print "  pip install winappdbg"
    exit(1)

class Listener:
    SOCKET_TIMEOUT = 10.0
    RECV_BUFFER_SIZE = 1024
    RECV_MAX_MSG_SIZE = 4

    def __init__(self, address="0.0.0.0", port=12345, max_connections=1):
        self._s = socket(AF_INET, SOCK_STREAM)
        self._s.setsockettimeout(SOCKET_TIMEOUT)
        self._s.bind( (address, port) )
        self._s.listen(max_connections)
    
    def start(self):
        while True:
            try:
                conn, addr = self._s.accept()
            except timeout:
                continue
            start_new_thread(self.process_connection, (conn, addr))

    def process_connection(self, conn, addr):
        print "accepted connection from engine: %s" % addr[0]
        try:
            while True:
                data = ""
                while True:
                    tmp = conn.recv(
                            RECV_BUFFER_SIZE, flags=socket.MSG_DONTWAIT)
                    if not tmp: break
                    data += tmp
                    if len(data) >= (self.RECV_MAX_MSG_SIZE * 1048576):
                        raise Exception(
                                "Connection::receive(): invalid message size")
                if not data:
                    break
                data = loads(data)
                command = getattr(self, "handle_command_" + data["command"])
                try:
                    response = command(data)
                except Exception:
                    print "error processing command %s from engine: %s" \
                                % (data["command"], addr[0])
                    print_exc()
                if response is None:
                    response = "failed"
                response = {"command": data["command"], "data": response}
                response = dumps(response)
                conn.sendall(response)
        except Exception:
            print "error processing command from engine: %s" % addr[0]
            print_exc()
        print "disconnected from engine: %s" % addr[0]

    def handle_command_ping(self, data):
        return "pong"

    def handle_command_start(self, data):
        # TO DO
        return "OK"

    def handle_command_status(self, data):
        # TO DO
        return "OK"

    def handle_command_kill(self, data):
        # TO DO
        return "success"

