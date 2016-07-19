# TachyonNet

A project which will listen on all TCP/UDP ports, and log the first
X number of bytes sent to the socket.   X is defined as 8192 bytes
by default.

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


## TODO:
* signal handling

