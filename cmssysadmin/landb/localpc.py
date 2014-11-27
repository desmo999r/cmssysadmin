import os
import socket
import dmidecode
import json
import re
import logging
import requests
from subprocess import Popen, PIPE
from cmssysadmin.landb.landbproxy import LanDBProxy

RACKINFOSERVER = 'kvm-s3562-1-ip137-11.cms:8000'
logger = logging.getLogger(__name__)
try: 
	atoken = os.environ['LANDB_TOKEN']
except KeyError as err:
	logger.info("LANDB_TOKEN environment variable does not exist.")

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

# This code as to be run as root
class LocalPC(object):
	_registered = False
	_rackInfo = {}
	_cms_nic = {}
	_bmc_nic = {}
	_deviceInput = {}
	_speedString = { 1000: 'GIGABITETHERNET',
			10000: 'TENGIGABITETHERNET', }

	@property
	def MACAddress(self):
		"""Returns the PC first NIC MAC address. Will return BOOTIF MAC address if specified on kernel cmd line or 'em1' or 'eth0' MAC address"""
		try:
			with open('/proc/cmdline', 'r') as f:
				cmdline = f.readline()
				return re.search('BOOTIF=([a-f0-9-]*)', cmdline).group(1)
		except Exception:
			logger.info("Cannot get the MAC from BOOTIF parameter, trying something else")

		return self.CMSNetworkCard['HardwareAddress']


	@property
	def CMSNetworkCard(self):
		"""Returns dictionary containing information about first NIC that can be used with LanDB SOAP interface."""
		if self._cms_nic:
			return self._cms_nic

		try:
			with open('/sys/class/net/em1/address', 'r') as f:
				mac = f.readline().strip()
			with open('/sys/class/net/em1/speed', 'r') as f:
				speed = int(f.readline().strip())
		except Exception:
			logger.warning("No 'em1' interface. Let's try with 'eth0'")
			try:
				with open('/sys/class/net/eth0/address', 'r') as f:
					mac = f.readline().strip()
				with open('/sys/class/net/eth0/speed', 'r') as f:
					speed = int(f.readline().strip())
			except Exception:
				logger.error("No 'eth0' interface. Giving up...")
				raise Exception("Cannot get MAC address.")

		self._cms_nic = {'HardwareAddress': mac, 'CardType': self._speedString[speed]}
		logger.info("CMS NIC: {0}".format(self._cms_nic))
		return self._cms_nic

	@property
	def CMSBulkInterface(self):
		cms_bulk = self.getBulkInterface(self.CMSNetworkCard)
		cms_bulk['InterfaceName'] = "%s--cms.cern.ch" % self.rackInfo['machine_name'] 
		return cms_bulk

	@property
	def BMCNetworkCard(self):
		# Getting BMC NIC
		if self._bmc_nic:
			return self._bmc_nic

		try:
			ipmi = Popen(['ipmitool', 'lan', 'print'], stdout=PIPE).communicate()
			findMac = re.compile('(([a-f0-9]{2}:){5}[a-f0-9]{2})')
			mac = findMac.search(ipmi[0]).group(0)
			# We assume the BMC NIC is a GIGABITETHERNET
			self._bmc_nic = {'HardwareAddress': mac, 'CardType': self._speedString[1000]}
		except Exception as e:
			# Something went wrong here. Maybe no BMC?
			# We log the message and continue.
			logger.warning("Cannot get BMC information: {0}".format(e))

		logger.info("BMC NIC: {0}".format(self._bmc_nic))
		return self._bmc_nic

	@property
	def BMCBulkInterface(self):
		bmc_bulk = self.getBulkInterface(self.BMCNetworkCard)
		bmc_bulk['InterfaceName'] = "%s-ipmi--cms.cern.ch" % self.rackInfo['machine_name'] 
		return bmc_bulk

	def getBulkInterface(self, card):
		swInfo = self._landbproxy.swInfo
		
		return {
				'InterfaceName': 'TODO',
				'OutletLabel': 'AUTO',
				'SecurityClass': 'USER',
				'InternetConnectivity': 0,
				'Location': {
						'Building': swInfo['Location']['Building'],
						'Floor': swInfo['Location']['Floor'],
						'Room': swInfo['Location']['Room'],
				},
				'Medium': 'TODO',
				'SwitchName': self._landbproxy.connection[0],
				'PortNumber': self._landbproxy.connection[1],
				'CableNumber': self._landbproxy.connection[1],
				'Medium': card['CardType'],
				'BindHardwareAddress': card['HardwareAddress'],
			}

	@property
	def rackInfo(self):
		if self._rackInfo:
			return self._rackInfo
		swName, swPort = self._landbproxy.connection
		rackName = self._landbproxy.location
		headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' }
		url = 'http://%s/api/racklayout/%s/%d' % (RACKINFOSERVER, rackName, swPort)
		self._rackInfo = requests.get(url, headers=headers).json()

		return self._rackInfo

	def __init__(self):
		if os.getuid() != 0:
			raise Exception("This code must be run as root")

		dmixml = dmidecode.dmidecodeXML()
		dmixml.SetResultType(dmidecode.DMIXML_DOC)
		self.xp = dmixml.QuerySection('all').xpathNewContext()
		mac = self.MACAddress
		if 'atoken' in globals():
			self._landbproxy = LanDBProxy(mac, atoken=atoken)
		else:
			self._landbproxy = LanDBProxy(mac)
	
	@property
	def isVirtual(self):
		if self.get_SystemInfo_ProductName() == 'KVM':
			return True
		else:
			return False

	@property
	def manufacturer(self):
		manuf = self.get_SystemInfo_Manufacturer()
		if re.match("(Dell|Dell Inc.)", manuf, re.IGNORECASE):
			return 'Dell'
		else:
			return manuf

	@property
	def deviceInfo(self):
		swInfo = self._landbproxy.swInfo
		machineShortName = self.rackInfo['machine_name']

		return {
			'DeviceName': machineShortName + '--cms',
			'Location': {
					'Building': swInfo['Location']['Building'],
					'Floor': swInfo['Location']['Floor'],
					'Room': swInfo['Location']['Room'],
			},
			'Zone': swInfo['Zone'],
			'Manufacturer': self.manufacturer,
			'Model': self.get_SystemInfo_ProductName(),
			'OperatingSystem': { 'Name': 'Linux', 'Version': 'SLC6' },
			'SerialNumber': self.get_SystemInfo_SerialNumber(),
			'ResponsiblePerson': {
				'Department': 'PH',
				'FirstName': 'E-GROUP',
				'Group': 'CMD',
				'Name': 'CMS-NET-ADMINS',
			},
			'HCPResponse': 0,
		}

	def register(self):
		logger.info("About to register machine: %s", self.rackInfo['machine_name'])
		self._registered = self._landbproxy.autoRegister(self.deviceInfo,
				[self.CMSNetworkCard, self.BMCNetworkCard],
				[self.CMSBulkInterface, self.BMCBulkInterface])
		logger.info("Registration done: %s", str(self._registered))
#		self.landbproxy.registerPC()
#		self.landbproxy.registerCard(pc['DeviceName'], self.getCMSNetworkCard())
#		self.landbproxy.registerCard(pc['DeviceName'], self.getBMCNetworkCard())
#		self.landbproxy.registerInterface(pc['DeviceName'], self.getCMSBulkInterface())
#		self.landbproxy.registerInterface(pc['DeviceName'], self.getBMCBulkInterface())

	def __str__(self):
		if self._registered:
			# Looks like we are now registered in LanDB
			msg = """
Machine is registered in IT LanDB.

Add the following line to 'assignments.csv':

%s

and this one to 'locations.csv':

%s

"""
			assignments = "%s,%s" % (self.rackInfo['machine_name'], self.get_SystemInfo_SerialNumber())
			swInfo = self._landbproxy.swInfo
			locations = ('{name},{loc},"{manuf}","{type}",{os},{os_ver},{bld},{floor},'
			'AUTO,AUTO/{port},{swName},{port},{port}').format(
					name=self.rackInfo['machine_name'],
					loc=self._landbproxy.location,
					manuf=self.manufacturer,
					type=self.get_SystemInfo_ProductName(),
					os="Linux",
					os_ver="SLC6",
					bld=swInfo['Location']['Building'],
					floor=swInfo['Location']['Floor'],
					swName=swInfo['DeviceName'],
					port=self._landbproxy.connection[1],
			)
			return msg % (assignments, locations)
		else:
			msg = '''\
Something went wrong.

Please log on and check what happened.
			'''
			raise Exception(msg)




# Don't want to write the same code over and over for all the
# DMI nodes so I dynamically create 'getter' functions.
def addGetter(cls, *args):
	name = "get"
	path = "/dmidecode"
	for i in  args:
		path = "%s/%s" % (path, i)
		name = "%s_%s" % (name, i)
	def getter(self):
		logger.info("Getting %s from DMI info" % path)
		data = self.xp.xpathEval(path)
		for d in data:
			return d.get_content()
		raise Exception("There is nothing for path: %s" % path)
	getter.__doc__ = "Docstring for %s" %name
	getter.__name__ = name
	setattr(cls, name, getter)

addGetter(LocalPC, 'SystemInfo', 'Manufacturer')
addGetter(LocalPC, 'SystemInfo', 'ProductName')
addGetter(LocalPC, 'SystemInfo', 'SerialNumber')
# vim: set ts=2 sw=2 tw=0 noet :
