#!/usr/bin/env python

import resource
import select
import socket
import struct
import time
import threading
import syslog
import os
import Queue
from datetime import datetime


class TachyonNet:

    THREADLIST = []
    ALLSOCKETS = []
    fd2sock = {}
    done = False
    LOGQ = Queue.Queue()

    def __init__(self, bind_addr='0.0.0.0', minport=1024, maxport=32767,
                 timeout=500, tcp_reset=False, bufsize=8192, backlog=32,
                 tcp_threads=32, udp_threads=32,
                 logdir='%s/.tachyon_net' % (os.path.expanduser('~'))):

        self.bind_addr = bind_addr
        self.minport = minport
        self.maxport = maxport
        self.timeout = timeout
        self.tcp_reset = tcp_reset
        self.bufsize = bufsize
        self.backlog = backlog
        self.tcp_threads = tcp_threads
        self.udp_threads = udp_threads
        self.logdir = logdir
        self.logfile = '%s/tn.log' % (self.logdir)
        return

    def run(self):
        r_ports = self.maxport - self.minport
        r_nofile = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        r_nofile_req = r_ports * 2.5
        if r_nofile < r_nofile_req:
            raise Exception(
                '[-] ERROR: INSUFFICIENT AVAILABLE FILE DESCRIPTORS.\n' +
                '[-] Trying to listen on %d TCP/UDP ports.\n' % (r_ports) +
                '[-] %d file descriptors are available.\n' % (r_nofile) +
                '[-] %d file descriptors are required.\n' % (r_nofile_req) +
                '[-] Modify /etc/security/limits.conf (Debian) ' +
                'OR reduce the port count.'
            )

        # open syslog
        syslog.openlog(
            logoption=syslog.LOG_PID,
            facility=syslog.LOG_USER
        )

        # check logdir
        if not os.path.exists(self.logdir):
            os.mkdir(self.logdir)

        # start logger thread
        t = threading.Thread(target=self.logger)
        t.name = '_logger'
        t.daemon = True
        t.start()
        print '[+] Logging to syslog, and directory: [%s]' % (self.logdir)

        self.start_tcp_threads()
        self.start_udp_threads()

        # loops and waits
        while not self.done:
            time.sleep(10)

        for t in self.THREADLIST:
            t.join()
        return

    def stop(self):
        self.done = True
        return

    def logger(self):
        lf = open(self.logfile, 'a')
        while True:
            d = self.LOGQ.get()
            if d[0] == 'msg':
                syslog.syslog(d[1])
                now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                lf.write('%s: %s\n' % (now, d[1]))
                lf.flush()
            elif d[0] == 'data':
                self.logger_writedata(d[1])
            self.LOGQ.task_done()

    def logger_writedata(self, msg):
        proto = msg[0]
        src = msg[1]
        dst = msg[2]
        data = msg[3]
        directory = '%s/%s' % (
            self.logdir,
            datetime.utcnow().strftime('%Y%m%d')
        )
        if not os.path.exists(directory):
            os.mkdir(directory)
        filename = '%s/%s_%s_%s__%s_%s.log' % (
            directory, proto.lower(),
            src[0], src[1], dst[0], dst[1]
        )
        f = open(filename, 'w')
        f.write(data)
        f.close()
        return

    def do_msglog(self, msg):
        self.LOGQ.put(('msg', msg))

    def do_datalog(self, proto, src, dst, data):
        self.LOGQ.put(('data', (proto, src, dst, data)))

    def start_tcp_threads(self):
        tcp_ports2thread = [[] for x in range(self.tcp_threads)]
        for i in range(self.minport, self.maxport):
            tcp_ports2thread[i % self.tcp_threads].append(i)

        for i in range(self.tcp_threads):
            t = threading.Thread(
                target=self.tcp_thread_main,
                args=[tcp_ports2thread[i % self.tcp_threads]]
            )
            t.name = '_tcp%02d' % (i)
            t.start()
            self.THREADLIST.append(t)
        print '[+] %d TCP listener threads active.' % (self.tcp_threads)
        return

    def start_udp_threads(self):
        udp_ports2thread = [[] for x in range(self.udp_threads)]
        for i in range(self.minport, self.maxport):
            udp_ports2thread[i % self.udp_threads].append(i)

        for i in range(self.udp_threads):
            t = threading.Thread(
                target=self.udp_thread_main,
                args=[udp_ports2thread[i % self.udp_threads]]
            )
            t.name = '_udp%02d' % (i)
            t.start()
            self.THREADLIST.append(t)
        print '[+] %d UDP listener threads active.' % (self.udp_threads)
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
                self.fd2sock[s.fileno()] = {'fileno': s, 'proto': 6}
                self.ALLSOCKETS.append(s)
                good += 1
            except socket.error as e:
                self.do_msglog('TCP: error binding port %d: %s' % (port, e))
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
                self.fd2sock[s.fileno()] = {'fileno': s, 'proto': 17}
                self.ALLSOCKETS.append(s)
                good += 1
            except socket.error as e:
                self.do_msglog(
                    'UDP: error binding port %d: %s' % (port, e)
                )
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

            self.do_msglog(
                '%s: %s:%d -> %s:%d: %d bytes read.' %
                (
                    sproto,
                    client_addr[0], client_addr[1],
                    server_addr[0], server_addr[1],
                    len(data)
                )
            )
            self.do_datalog(sproto, client_addr, server_addr, data)

        except Exception as e:
            self.do_msglog('ERROR: %s' % (e))
            pass
        return

    def __del__(self):
        for s in self.ALLSOCKETS:
            s.close()

if __name__ == '__main__':
    print 'This is the module.  You need to import and use this.'
