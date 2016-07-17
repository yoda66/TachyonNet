#!/usr/bin/env python

import select
import socket
import struct
import time
import threading


class TachyonNet:

    THREADLIST = []
    ALLSOCKETS = []
    fd2sock = {}
    done = False

    def __init__(self, bind_addr='0.0.0.0', minport=1024, maxport=65535,
                 timeout=500, tcp_reset=False, bufsize=8192, backlog=20,
                 tcp_threads=32, udp_threads=32):

        self.bind_addr = bind_addr
        self.minport = minport
        self.maxport = maxport
        self.timeout = timeout
        self.tcp_reset = tcp_reset
        self.bufsize = bufsize
        self.backlog = backlog
        self.tcp_threads = tcp_threads
        self.udp_threads = udp_threads

        self.start_tcp_threads()
        self.start_udp_threads()

        try:
            while not self.done:
                time.sleep(10)
        except KeyboardInterrupt:
            self.done = True

        print '[+] Exiting...'
        for t in self.THREADLIST:
            t.join()
        return

    def start_tcp_threads(self):
        tcp_ports2thread = [ [] for x in range(self.tcp_threads) ]
        for i in range(self.minport, self.maxport):
            tcp_ports2thread[i % self.tcp_threads].append(i)

        for i in range(self.tcp_threads):
            t = threading.Thread(
                target=self.tcp_thread_main,
                args=[ tcp_ports2thread[i % self.tcp_threads] ]
            )
            t.name = '_tcp%02d' % (i)
            t.start()
            self.THREADLIST.append(t)
        return

    def start_udp_threads(self):
        udp_ports2thread = [ [] for x in range(self.udp_threads) ]
        for i in range(self.minport, self.maxport):
            udp_ports2thread[i % self.udp_threads].append(i)

        for i in range(self.udp_threads):
            t = threading.Thread(
                target=self.udp_thread_main,
                args=[ udp_ports2thread[i % self.udp_threads] ]
            )
            t.name = '_udp%02d' % (i)
            t.start()
            self.THREADLIST.append(t)
        return

    def tcp_thread_main(self, portlist):
        mux = self.bind_tcp_sockets(portlist)
        self.tcp_connections(mux)
        return

    def udp_thread_main(self, portlist):
        mux = self.bind_udp_sockets(portlist)
        self.udp_connections(mux)
        return

    def bind_tcp_sockets(self, portlist):
        good = 0
        bad = 0
        mux = select.poll()
        for port in portlist:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind((self.bind_addr, port))
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

    def bind_udp_sockets(self, portlist):
        good = 0
        bad = 0
        mux = select.poll()
        for port in portlist:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind((self.bind_addr, port))
                mux.register(s)
                self.fd2sock[s.fileno()] = { 'fileno': s, 'proto': 17 }
                self.ALLSOCKETS.append(s)
                good += 1
            except socket.error as e:
                print '[-] UDP: error binding port %d: %s' % (port, e)
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

    def udp_connections(self, mux):
        while not self.done:
            ready = mux.poll()
            for fd, event in ready:
                if event & select.POLLIN:
                    self.read_data(fd)
            time.sleep(self.timeout / 1000.0)
        return

    def read_data(self, fd):
        s = self.fd2sock[fd]['fileno']
        proto = self.fd2sock[fd]['proto']
        server_addr = s.getsockname()
        try:
            if proto == 6:
                sproto = 'TCP'
                cs, client_addr = s.accept()
                data = cs.recv(self.bufsize)
                cs.close()
            elif proto == 17:
                sproto = 'UDP'
                data, client_addr = s.recvfrom(self.bufsize)

            print '[+] %s: %s:%d -> %s:%d: %d bytes read.' % (
                sproto,
                client_addr[0], client_addr[1],
                server_addr[0], server_addr[1],
                len(data)
            )

        except Exception as e:
            print '[-] ERROR: %s' % (e)
            pass
        return

    def __del__(self):
        for s in self.ALLSOCKETS:
            s.close()

if __name__ == '__main__':
    p = TachyonNet(tcp_reset=True)
