#from cmssysadmin.landb.localpc import LocalPC
import logging
from cmssysadmin.foreman.foremanrestapi import ForemanRestAPI, NotFound

logger = logging.getLogger(__name__)
FOREMAN_HOST="kvm-s3562-1-ip137-13.cms"
FOREMAN_USER="autoregister"
FOREMAN_PASSWD="lss5install"

class Host(ForemanRestAPI):
	_data = {}

	def __init__(self, host, user, passwd):
		ForemanRestAPI.__init__(self, host, user, passwd)

	@classmethod
	def register(cls, localpc, hostgroup='base', build=False):
		host = cls(FOREMAN_HOST, FOREMAN_USER, FOREMAN_PASSWD)
		try:
			host._data = host.getHost("%s.cms" % localpc.shortName)
			logger.info("Host already exists %s", localpc.shortName)
		except NotFound, e:
			groupId = host.getHostGroupId(hostgroup)
			payload = {'host': { 
					'hostname': localpc.shortName,
					'mac': localpc.MACAddress,
					'hostgroup_id': groupId,
					'build': build
				}
			}
			logger.info("Creating new host in Foreman: %s", str(payload))
			host._data = host.post(payload, 'hosts').json()
		return host
