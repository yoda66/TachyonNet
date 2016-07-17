#!/usr/bin/env python

import select
import socket
import struct
import time
import threading


class TachyonNet:

    def __init__(self, minport=1024, maxport=8192, timeout=1000,
                 tcp_reset=False, bufsize=8192, backlog=20,
                 tcp_threads=32, udp_threads=16):

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

        self.threads = []
        tcp_ports2thread = [ [] for x in range(tcp_threads) ]
        for i in range(minport, maxport):
            tcp_ports2thread[i % tcp_threads].append(i)

        for i in range(tcp_threads):
            t = threading.Thread(
                target=self.tcp_thread_main,
                args=[ tcp_ports2thread[i % tcp_threads] ]
            )
            t.name = '_tcp%02d' % (i)
            t.start()
            self.threads.append(t)

        try:
            while not self.done:
                time.sleep(10)
        except KeyboardInterrupt:
            self.done = True

        print '[+] Exiting...'
        for t in self.threads:
            t.join()
        return

    def tcp_thread_main(self, portlist):
        mux = self.bind_tcp_sockets(portlist)
        self.tcp_connections(mux)
        return

    def bind_udp_sockets(self):
        good = 0
        bad = 0
        for port in range(self.minport, self.maxport):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind((self.addr, port))
                self.udpmux.register(s)
                self.fd2sock[s.fileno()] = { 'fileno': s, 'proto': 17 }
                self.ALLSOCKETS.append(s)
                good += 1
            except socket.error as e:
                bad += 1
                continue
        print '[*] UDP sockets: %d listening, %d failed.' % (good, bad)
        return

    def bind_tcp_sockets(self, portlist):
        good = 0
        bad = 0
        mux = select.poll()
        for port in portlist:
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
                mux.register(s)
                self.fd2sock[s.fileno()] = { 'fileno': s, 'proto': 6 }
                self.ALLSOCKETS.append(s)
                good += 1
            except socket.error as e:
                print '[-] TCP: error binding port %d: %s' % (port, e)
                bad += 1
                continue
        return mux

    def tcp_connections(self, mux):
        while not self.done:
            ready = mux.poll(self.timeout)
            for fd, event in ready:
                if event & select.POLLIN:
                    self.read_data(fd)
        return

    def read_data(self, fd):
        s = self.fd2sock[fd]['fileno']
        proto = self.fd2sock[fd]['proto']
        if proto == 6:
            try:
                cs, addr = s.accept()
                data = cs.recv(self.bufsize)
                print '[+] (%s) %15s:%05d TCP: %d bytes read' % (
                    threading.current_thread().name,
                    addr[0], addr[1], len(data)
                )
                cs.close()
            except:
                pass
        elif proto == 17:
            data, addr = s.recvfrom(self.bufsize)
            print '[+] (%s) %15s:%05d UDP: %d bytes read' % (
                threading.current_thread().name,
                addr[0], addr[1], len(data)
            )
        return

    def __del__(self):
        for s in self.ALLSOCKETS:
            s.close()

if __name__ == '__main__':
    p = TachyonNet(tcp_reset=True)
    #try:
    #    p.tcp_connections()
    #except KeyboardInterrupt:
    #    print 'CTRL-C received. Exit.'

