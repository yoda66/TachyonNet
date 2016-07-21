# TachyonNet

A project which will listen on all TCP/UDP ports, and log the first
X number of bytes sent to the socket.   X is defined as 8192 bytes
by default.

    IMPORTANT: A default linux installation will not have
    enough file descriptors allocated to open up
    65535 * 2 (TCP and UDP) sockets.  Within Ubuntu/Debian,
    see /etc/security/limits.conf file.

A structured log format will be created.  The default logging
directory is the home directory of the user who runs the program,
following by ".tachyon_net" and then a date stamp based
directory.

Example: If it is July 19, 2016 today, then TachyonNet will create
a logging directory as follows:

    ~/.tachyon_net/20160719/

Within this directory, you will find files representing TCP/IP
connections made to this system.  The first 8192 bytes (default)
of data received is written to this file.

    ls ~/.tachyon_net/20160719/
    tcp_127.0.0.1_54561__0.0.0.0_8080.log
    tcp_127.0.0.1_54562__0.0.0.0_8090.log

The file name itself consists of:

    proto_srcip_sport__dstip_dport.log

## Usage

    [*] ======================================
    [*]  TachyonNet Version 20160720_1.0
    [*]  Author: Joff Thyer (c) 2016
    [*]  Black Hills Information Security
    [*] ======================================

    usage: tn.py [-h] [--minport MINPORT] [--maxport MAXPORT] [-b BINDADDR]
             [-f FIN] [--bufsize BUFSIZE] [-t THREADS]

    optional arguments:
    -h, --help            show this help message and exit
    -b BINDADDR, --bindaddr BINDADDR
                          IP address to bind/listen on (defaults to all)
    --mintcp MINTCP       lowest TCP port in range to listen on (default: 1024)
    --maxtcp MAXTCP       highest TCP port in range to listen on (default:
                          32768)
    --minudp MINUDP       lowest UDP port in range to listen on (default: 1024)
    --maxudp MAXUDP       highest UDP port in range to listen on (default:
                          32768)
    --bufsize BUFSIZE     buffer size to capture traffic (default: 8192 bytes)
    -t THREADS, --threads THREADS
                          number of TCP/UDP threads (default: 32)
    --notcp               do not open TCP sockets
    --noudp               do not open UDP sockets
    -f, --fin             Use 3-way/4-way FIN/ACK to teardown connections
                          (defaults to TCP RESET)

## TODO:
* signal handling

