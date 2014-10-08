from foremanrestapi import ForemanRestAPI

class Host(ForemanRestAPI):
	def __init__(self, host, user, passwd):
		ForemanRestAPI.__init__(self, host, user, passwd, 'hosts')
		self.get("1", "2")

