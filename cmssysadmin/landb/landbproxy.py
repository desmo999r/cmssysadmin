import os
import re
import logging
from time import sleep
from suds import WebFault
from suds.client import Client 
from suds.sax.element import Element
from suds.xsd.doctor import ImportDoctor, Import

endpoint = "https://network.cern.ch/sc/soap/soap.fcgi?v=5&WSDL"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class LanDBProxy(object):
	_swInfo = {}
	_swName = ""
	_swPort = 0
	
	def __init__(self, mac, ip='', atoken = ''):
		imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
		d = ImportDoctor(imp)
		self._client = Client(endpoint, doctor=d, cache=None) 

		if atoken:
			authTok = Element('token').setText(atoken)
			authHeader = Element('Auth').insert(authTok)
			self._client.set_options(soapheaders=authHeader) 

		# Get connection information
		logger.info("Getting connection information from LanDB")
		if ip:
			conn = self._client.service.getCurrentConnection(ip, [mac])
		else:
			try:
				conn = self._client.service.getMyCurrentConnection([mac])
			except Exception:
				logger.info("Got an exception. Give it another try.")
				sleep(20)
				conn = self._client.service.getMyCurrentConnection([mac])
		if len(conn) == 0:
			raise Exception("No connection for %s %s" % (ip, mac)) 
		elif len(conn) > 1:
			raise Exception("Multiple connections for %s %s" % (ip, mac))
		self._swName = conn[0].SwitchName[0]
		logger.debug("Switch name %s", self._swName)
		self._swPort = int(conn[0].SwitchPort[0])
		logger.debug("Switch port %s", self._swPort)

		# Get switchInfo
		logger.info("Getting switch info from LanDB")
		try:
			self._swInfo = self._client.service.getDeviceBasicInfo(self._swName)
		except Exception:
			logger.info("Got an exception. Give it another try.")
			sleep(20)
			self._swInfo = self._client.service.getDeviceBasicInfo(self._swName)
		logger.info("Switch info: {0}".format(self._swInfo))

	@property
	def connection(self):
		return self._swName, self._swPort

	@property
	def swInfo(self):
		return self._swInfo

	@property
	def location(self):
		return self.swInfo['Zone'].lower()


	def registerPC(self, pc):
		self._client.service.deviceInsert(pc)

	def registerCard(self, pcName, card):
		self._client.service.deviceAddCard(pcName, card)

	def registerInterface(self, pcName, interface):
		self._client.service.deviceAddBulkInterface(pcName, interface)

	def autoRegister(self, pc, cards, interfaces):
		try:
			dev = self._client.service.getDeviceBasicInfo(pc['DeviceName'])
			logger.info("Device already registered")
			if (dev['SerialNumber'] != pc['SerialNumber']):
				# Same name but different serial number. We have a problem
				raise Exception("Same name (%s) but different serial numbers" % pc['DeviceName']) 
			return True
		except WebFault, e:
			return self._client.service.bulkInsertAuto(pc, cards, interfaces)
# vim: set ts=2 sw=2 tw=0 noet :
