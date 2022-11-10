#!/bin/sh

killall nc
mkfifo /tmp/vnctcp
mkfifo /tmp/vncudp
(nc -l 30101 < /tmp/vnctcp | nc localhost 5900 > /tmp/vnctcp ) &
(nc -lu 30101 < /tmp/vncudp | nc -u localhost 5900 > /tmp/vncudp) &
