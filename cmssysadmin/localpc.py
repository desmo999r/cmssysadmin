import os
import socket
import dmidecode
import json
import re
import logging
import requests
import ConfigParser
from time import sleep
from subprocess import Popen, PIPE, call
from cmssysadmin.landb.landbproxy import LanDBProxy
from cmssysadmin.foreman import Host
from cmssysadmin import get_bootif, get_ip_address

config = ConfigParser.ConfigParser()
config.read('/etc/cmssysadmin.conf')
RACKINFOSERVER = config.get('cmssysadmin', 'rackinfo_server')

logger = logging.getLogger(__name__)
try: 
	atoken = os.environ['LANDB_TOKEN']
except KeyError as err:
	logger.info("LANDB_TOKEN environment variable does not exist.")

# This code as to be run as root
class LocalPC(object):
	_registered = False
	_rackInfo = {}
	_cms_nic = {}
	_cms_dev = ''
	_bmc_nic = {}
	_deviceInput = {}
	_speedString = { 1000: 'GIGABITETHERNET',
			10000: 'TENGIGABITETHERNET', }

	@property
	def MACAddress(self):
		"""Returns the PC first NIC MAC address. Will return BOOTIF MAC address if specified on kernel cmd line or 'em1' or 'eth0' MAC address"""
		return self.CMSNetworkCard['HardwareAddress']


	@property
	def CMSDev(self):
		return self._cms_dev

	@property
	def CMSNetworkCard(self):
		"""Returns dictionary containing information about first NIC that can be used with LanDB SOAP interface."""
		return self._cms_nic

	@property
	def CMSBulkInterface(self):
		cms_bulk = self.getBulkInterface(self.CMSNetworkCard)
		cms_bulk['InterfaceName'] = "%s--cms.cern.ch" % self.rackInfo['machine_name'] 
		return cms_bulk

	@property
	def BMCNetworkCard(self):
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
		return self._rackInfo

	def __init__(self):
		if os.getuid() != 0:
			raise Exception("This code must be run as root")

		dmixml = dmidecode.dmidecodeXML()
		dmixml.SetResultType(dmidecode.DMIXML_DOC)
		self.xp = dmixml.QuerySection('all').xpathNewContext()

		# Get CMS Card info
		try:
			# The CMS interface is the boot interface identified by BOOTIF in /proc/cmdline
			self._cms_dev, mac = get_bootif()
			with open('/sys/class/net/' + self._cms_dev + '/speed', 'r') as f:
				speed = int(f.readline().strip())
		except Exception:
			logger.error("No 'eth0' interface. Giving up...")
			raise Exception("Cannot get MAC address.")

		self._cms_nic = {'HardwareAddress': mac, 'CardType': self._speedString[speed]}
		logger.info("CMS NIC: {0}".format(self._cms_nic))

		# Get BMC Card info
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

		# Create the LanDB proxy which gets information form LanDB service
		mac = self._cms_nic['HardwareAddress']
		if 'atoken' in globals():
			self._landbproxy = LanDBProxy(mac, atoken=atoken)
		else:
			self._landbproxy = LanDBProxy(mac)
	
		swName, swPort = self._landbproxy.connection
		rackName = self._landbproxy.location
		headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' }
		url = 'http://%s/api/racklayout/%s/%d' % (RACKINFOSERVER, rackName, swPort)
		logger.info("Trying to get racklayout info from: ".format(url))
		self._rackInfo = requests.get(url, headers=headers).json()
		self._fqdn = '%s--cms.cern.ch.' % self._rackInfo['machine_name']
		self._shortname = self._rackInfo['machine_name']

	@property
	def FQDN(self):
		return self._fqdn

	@property
	def shortName(self):
		return self._shortname

	@property
	def finalIP(self):
		try:
			ip = socket.gethostbyname(self.shortName)
			logger.info("%s => %s", self.shortName, ip)
			return ip
		except socket.gaierror:
			logger.info("No IP associated to %s", self.shortName)
			return ''

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

	def registerForeman(self):
		logger.info("About to register machine %s in Foreman", self.shortName)
		self._foremanHost = Host.register(self)
		logger.info("Foreman registration is done")

	def waitForFinalIP(self):
		logger.info('Starting to wait for our final IP')
		while True:
			# Release the previous DHCP lease and clean up everything
			# before launching a new dhclient
			call(['/sbin/dhclient', '-r', self.CMSDev])
			call(['rm', '-f', '/var/lib/dhclient/*'])
			dhclient = Popen(['/sbin/dhclient', '-d' , self.CMSDev])
			sleep(60)
			if self.finalIP == get_ip_address(self.CMSDev):
				logger.info("We got our final IP")
				break

	def __str__(self):
		if self._registered:
			# Looks like we are now registered in LanDB
			msg = """
Machine is registered in IT LanDB.

Add the following line to 'assignments.csv' and 'location.csv':

'serial_number.csv' should be a link to a .csv file. Make sure the link exists and points to the right file.

echo '%s' >> assignments.csv
echo '%s' >> locations.csv
echo '%s' >> ../serial_number.csv

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
			serial = "%s,%s" % (self.get_SystemInfo_SerialNumber(), self._cms_nic['HardwareAddress'])
			return msg % (assignments, locations, serial)
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
