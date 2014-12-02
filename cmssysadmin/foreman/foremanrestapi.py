import requests
import json
import urllib
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def formatUrl(host, args):
	url = 'https://{0}/api'.format(host)
	for i in args:
		url = "{0}/{1}".format(url, i)
	return url

class NotFound(Exception):
	def __init__(self, msg):
		Exception.__init__(self, msg)

def checkResponse(response):
	if response.status_code == 200:
		pass
	elif response.status_code == 404:
		raise NotFound("Object not found: {0} {1}".format(response.status_code, response.reason))
	else:
		raise Exception("Something went wrong with Foreman REST API: {0} {1}".format(response.status_code, response.reason))

class ForemanRestAPI(object):
	headers = { 'Content-Type': 'application/json', 'Accept': 'application/json;version=2' }

	def get(self, *args):
		url = formatUrl(self.host, args)
		logger.debug("Sending GET to %s", url)
		response = requests.get(url, verify=False,
				headers=self.headers,
				auth=(self.user, self.passwd))
		checkResponse(response)
		return response

	def post(self, payload = {}, *args):
		url = formatUrl(self.host, args)
		logger.debug("Sending POST to %s", url)
		response = requests.post(url, data=json.dumps(payload), verify=False,
				headers=self.headers,
				auth=(self.user, self.passwd))
		checkResponse(response)
		return response

	def getHostGroupId(self, hostgroupName):
		response = self.get('hostgroups', hostgroupName)
		return response.json()[u'id']


	def registerNewHost(self, host, mac, groupId, build=False):
		payload = {'host': { 
				'hostname': host,
				'mac': mac,
				'hostgroup_id': groupId,
				'build': build
			}
		}
		return self.post(payload, 'hosts').json()

	def getHost(self, hostname):
		response = self.get('hosts', hostname)
		return response.json()

	def __init__(self, host, user, passwd):
		self.user = user
		self.passwd = passwd
		self.host = host
