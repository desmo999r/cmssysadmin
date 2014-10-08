#!/usr/bin/env python
def testfct(a, *s):
	print a, s

if __name__ == '__main__':
	import os
	from foremanrestapi import ForemanRestAPI
	try:
		foreman = ForemanRestAPI(os.environ['FOREMAN_HOST'], 
				os.environ['FOREMAN_USER'], os.environ['FOREMAN_PASSWD'])
		foreman.registerNewHost('test', '02:0c:11:50:00:30', 
				foreman.getHostGroupId('stresstest'))
	except KeyError, e:
		print "At least one environment variable is missing: ", e
