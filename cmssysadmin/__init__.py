import os
import socket
import fcntl
import struct
import subprocess
import logging

logger = logging.getLogger(__name__)

class CmdLine(object):
    options = {}

    class __metaclass__(type):
        def __new__(cls, *kargs, **kwargs):
            t = type.__new__(cls, *kargs, **kwargs)
            with open("/proc/cmdline") as f:
                for option in f.readline().strip().split():
                    fields = option.split("=")
                    if len(fields) == 1:
                        t.options[fields[0]] = True
                    else:
                        t.options[fields[0]] = fields[1]
            logger.info("/proc/cmdline options: " + str(t.options))
            return t

def get_bootif():
    try:
        mac = CmdLine.options['BOOTIF'][3:].replace('-', ':').strip().lower()
    except KeyError:
        return None
    for n in os.listdir("/sys/class/net"):
        with open("/sys/class/net/" + n + "/address") as f:
            if mac == f.read().strip().lower():
                return n, mac
    raise Exception("There is a BOOTIF param but no matching interface")

def get_ip_address(ifname):
	"""Returns the NIC current IPv4 address"""
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	ip = socket.inet_ntoa(fcntl.ioctl(
		s.fileno(),
		0x8915,  # SIOCGIFADDR
		struct.pack('256s', ifname[:15])
	)[20:24])
	logger.info("Current IP is %s", ip)
	return ip

# vim: set ts=4 sw=4 tw=0 et :
