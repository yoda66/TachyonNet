#!/usr/bin/env python

import select
import socket
import struct
import time


class TachyonNet:

    def __init__(self, minport=2000, maxport=2050, timeout=5000,
                 tcp_reset=False, bufsize=8192, backlog=20):
        self.addr = '0.0.0.0'
        self.timeout = timeout
        self.tcp_reset = tcp_reset
        self.minport = minport
        self.maxport = maxport
        self.backlog = backlog
        self.bufsize = bufsize
        self.done = False
        self.ALLSOCKETS = []
        self.fd2sock = {}
        self.mux = select.poll()
        self.bind_udp_sockets()
        self.bind_tcp_sockets()
        return

    def bind_udp_sockets(self):
        good = 0
        bad = 0
        for port in range(self.minport, self.maxport):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind((self.addr, port))
                self.mux.register(s)
                self.fd2sock[s.fileno()] = { 'fileno': s, 'proto': 17 }
                self.ALLSOCKETS.append(s)
                good += 1
            except socket.error as e:
                bad += 1
                continue
        print '[*] UDP sockets: %d listening, %d failed.' % (good, bad)
        return

    def bind_tcp_sockets(self):
        good = 0
        bad = 0
        for port in range(self.minport, self.maxport):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind((self.addr, port))
                s.listen(self.backlog)
                s.setblocking(0)
                if self.tcp_reset:
                    s.setsockopt(
                        socket.SOL_SOCKET,
                        socket.SO_LINGER,
                        struct.pack('ii', 1, 0)
                    )
                self.mux.register(s)
                self.fd2sock[s.fileno()] = { 'fileno': s, 'proto': 6 }
                self.ALLSOCKETS.append(s)
                good += 1
            except socket.error as e:
                bad += 1
                continue
        print '[*] TCP sockets: %d listening, %d failed.' % (good, bad)

    def tcp_connections(self):
        while not self.done:
            """
            If UDP sockets in MIX, timeout param does not
            apply.  We need separate threads for UDP versus
            TCP.
            """
            ready = self.mux.poll(1)
            for fd, event in ready:
                if event & select.POLLIN:
                    self.read_data(fd)
            time.sleep(0.1)
        return

    def read_data(self, fd):
        s = self.fd2sock[fd]['fileno']
        proto = self.fd2sock[fd]['proto']
        if proto == 6:
            cs, addr = s.accept()
            data = cs.recv(self.bufsize)
            print '[+] %15s:%05d TCP: %d bytes read' % (
                addr[0], addr[1], len(data)
            )
            cs.close()
        elif proto == 17:
            data, addr = s.recvfrom(self.bufsize)
            print '[+] %15s:%05d UDP: %d bytes read' % (
                addr[0], addr[1], len(data)
            )
        return

    def __del__(self):
        for s in self.ALLSOCKETS:
            s.close()

if __name__ == '__main__':
    p = TachyonNet(tcp_reset=True)
    try:
        p.tcp_connections()
    except KeyboardInterrupt:
        print 'CTRL-C received. Exit.'

