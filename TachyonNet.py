#!/usr/bin/env python

import select
import socket
import struct


class PacketTrap:

    def __init__(self, minport=2000, maxport=3000,
                 tcp_reset=False, bufsize=8192, backlog=20):
        self.addr = '0.0.0.0'
        self.timeout = 5
        self.tcp_reset = tcp_reset
        self.minport = minport
        self.maxport = maxport
        self.backlog = backlog
        self.bufsize = bufsize
        self.done = False
        self.ALLSOCKETS = []
        self.fd2sock = {}
        self.tcpmux = select.poll()
        self.bind_tcp_sockets()
        return

    def bind_udp_sockets(self):
        return

    def bind_tcp_sockets(self):
        good = 0
        bad = 0
        for port in range(self.minport, self.maxport+1):
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
                self.tcpmux.register(s)
                self.fd2sock[s.fileno()] = s
                self.ALLSOCKETS.append(s)
                good += 1
            except socket.error as e:
                bad += 1
                continue
        print '[*] TCP sockets: %d listening, %d failed.' % (good, bad)

    def tcp_connections(self):
        while not self.done:
            ready = self.tcpmux.poll()
            for s, event in ready:
                self.tcp_accept_read(s)
        return

    def tcp_accept_read(self, s):
        cs, addr = self.fd2sock[s].accept()
        data = cs.recv(self.bufsize)
        print '[+] %15s:%05d TCP: %d bytes read' % (
            addr[0], addr[1], len(data)
        )
        cs.close()
        return

    def __del__(self):
        for s in self.ALLSOCKETS:
            self.tcpmux.unregister(s)
            s.close()

if __name__ == '__main__':
    p = PacketTrap(tcp_reset=True)
    try:
        p.tcp_connections()
    except KeyboardInterrupt:
        print 'CTRL-C received. Exit.'

