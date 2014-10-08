import requests
import json
import urllib

class ForemanRestAPI(object):
	headers = { 'Content-Type': 'application/json', 'Accept': 'application/json;version=2' }

	def get(self, *args):
		url = 'https://{0}/api'.format(self.host)
		for i in args:
			url = "{0}/{1}".format(url, i)
		response = requests.get(url, verify=False,
				headers=self.headers,
				auth=(self.user, self.passwd))
		if response.status_code != 200:
			raise Exception("Something went wrong with the REST API request: {0} {1}".format(response.status_code, response.reason))
		return response

	def post(self, payload = {}, *args):
		url = 'https://{0}/api'.format(self.host)
		for i in args:
			url = "{0}/{1}".format(url, i)
		response = requests.post(url, data=json.dumps(payload), verify=False,
				headers=self.headers,
				auth=(self.user, self.passwd))
		if response.status_code != 200:
			raise Exception("Something went wrong with the REST API request: {0} {1}".format(response.status_code, response.reason))

	def getHostGroupId(self, hostgroupName):
		response = self.get('hostgroups', hostgroupName)
		return reponse.json()[u'id']


	def registerNewHost(self, host, mac, groupId, build=True):
		payload = {'host': { 
				'hostname': host,
				'mac': mac,
				'hostgroup_id': groupId,
				'build': build
			}
		}
		self.post(payload, 'hosts')


	def __init__(self, host, user, passwd):
		self.user = user
		self.passwd = passwd
		self.host = host
