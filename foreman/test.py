#!/usr/bin/env python
import argparse
import os
import sys
from foremanrestapi import ForemanRestAPI
	
def show(args):
	print foreman.getHost(args.hostname)

def register(args):
	foreman.registerNewHost(args.hostname, args.mac,
			foreman.getHostGroupId(args.hostgroup), build=args.build)

parser = argparse.ArgumentParser()
subparser = parser.add_subparsers(title='Actions')

parser_show = subparser.add_parser('show', help='Get host information')
parser_show.add_argument('hostname', help='the FQDN (with .CMS)')
parser_show.set_defaults(action=show)

parser_register = subparser.add_parser('register', help="Register a new host")
parser_register.add_argument('hostname', help='hostname without .CMS')
parser_register.add_argument('-m', metavar='macaddress', 
		dest="mac", help='The host macaddress', required=True)
parser_register.add_argument('-g', metavar='hostgroup', 
		dest="hostgroup", help='The Foreman HostGroup the host belongs to', required=True)
parser_register.add_argument('-b', action='store_true', dest="build", 
		default=False, help='Foreman will rebuild the host when it is rebooted')
parser_register.set_defaults(action=register)

args = parser.parse_args()

try:
	foreman = ForemanRestAPI(os.environ['FOREMAN_HOST'], 
			os.environ['FOREMAN_USER'], os.environ['FOREMAN_PASSWD'])
except KeyError, e:
	print "At least one environment variable is missing: ", e
	sys.exit(2)

args.action(args)
