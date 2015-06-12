# $Id$
#

# Standard libraries
import time
import sys
import os
import argparse
import logging

# XML specific libraries
from lxml import etree
from lxml.builder import E

# Junos Ez
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import *
from jnpr.junos.factory import loadyaml
from jnpr.junos.op import *

# External
import yaml
import paramiko
import csv
from influxdb.influxdb08 import InfluxDBClient
from pprint import pprint
from pprint import pprint


#################################################

# Specific functions

# Simple math auxiliary function to convert BW values  

def get_bps (bwstring):

	if ('M' in bwstring):
		return int(float(bwstring.split('M')[0])*10**6)
	elif ('m' in bwstring):
		return int(float(bwstring.split('m')[0])*10**6)
	elif ('k' in bwstring):
		return int(float(bwstring.split('k')[0])*10**3)
	elif ('K' in bwstring):
		return int(float(bwstring.split('K')[0])*10**3)
	elif ('t' in bwstring):
		return int(float(bwstring.split('t')[0])*10**9)
	elif ('T' in bwstring):
		return int(float(bwstring.split('T')[0])*10**9)
	else:
		return int(bwstring.strip('bps'))

# Function to clear all stats and reinitialize normalization 

def initialize (containerlsp,dev):

	# RPC to clear all interface stats
	dev.rpc.clear_interfaces_statistics_all()
	# RPC to clear Container LSP and resignal members
	dev.rpc.clear_mpls_container_lsp_information(regex=containerlsp, optimize_aggressive=True)
	# RPC to clear all mpls lsp stats
	dev.rpc.clear_mpls_lsp_information(statistics=True)

# Function with RPC to obtain member-lsps in container-lsp 

def get_member_lsp_summary (containerlsp,dev,db):
	# RPC to obtain member-lsps in container-lsp 
	memberlspsummary = dev.rpc.get_mpls_container_lsp_information(regex=containerlsp)
	logging.info("---- Total number of member LSPs: %s ----",memberlspsummary.findtext('rsvp-session-data/mpls-container-lsp-member-summary/mpls-container-lsp/mpls-container-member-count'))
	memberlsp_json_body = [{
	 "name":"Number of member LSPs", 
	 "columns": ["value"],
	 "points": [[int(memberlspsummary.findtext('rsvp-session-data/mpls-container-lsp-member-summary/mpls-container-lsp/mpls-container-member-count'))],],
	 }]
	db.write_points(memberlsp_json_body,time_precision='s')

# Function with RPC to obtain member-lsps stats 

def get_member_lsp_stats (yamlfile,dev,db):

	# RPC to obtain container-lsp stats
	memberlspstats = loadyaml(yamlfile)
	globals().update(memberlspstats)
	lspstats = MemberLSPStatsTable(dev)
	lspstats.get()

	# Initialize variables for sum of lsps
	sumlsppackets = 0
	sumlspbytes = 0

	# Extract relevant information per route
	for memberlsp in lspstats:
	 logging.info("Member-LSP %s -- packets %s, bytes %s",memberlsp.name, memberlsp.packets, memberlsp.bytes)
	 sumlsppackets = sumlsppackets + int(memberlsp.packets)
	 sumlspbytes = sumlspbytes + int(memberlsp.bytes)

	 memberlsp_bytes_json_body = [{
	 "name": memberlsp.name + " LSP bytes",
	 "columns": ["value"],
	 "points": [[int(memberlsp.bytes)]],
	 }]
	 db.write_points(memberlsp_bytes_json_body,time_precision='s')
	 memberlsp_packets_json_body = [{
	 "name": memberlsp.name + " LSP packets",
	 "columns": ["value"],
	 "points": [[int(memberlsp.packets)]],
	 }]
	 db.write_points(memberlsp_packets_json_body,time_precision='s')


	# Writing stats and json for sum of all member LSPs stats
	logging.info("All member LSPs -- packets %s, bytes %s",sumlsppackets, sumlspbytes)
	sumlsp_packets_json_body = [{
	 "name": "All member LSP packets",
	 "columns": ["value"],
	 "points": [[sumlsppackets]],
	 }]
	db.write_points(sumlsp_packets_json_body,time_precision='s')
	sumlsp_bytes_json_body = [{
	 "name": "All member LSP bytes",
	 "columns": ["value"],
	 "points": [[sumlspbytes]],
	 }]
	db.write_points(sumlsp_bytes_json_body,time_precision='s')

# Function with RPC to obtain member-lsps BW 

def get_member_lsp_bw (yamlfile,dev,db):

	# RPC to obtain container-lsp stats
	memberlspbw = loadyaml(yamlfile)
	globals().update(memberlspbw)
	lspBW = MemberLSPMemberBWTable(dev)
	lspBW.get()

	# Initialize variables for sum of lsps
	sumlspavgBW = 0
	sumlspsignalBW = 0

	# Extract relevant information per route
	for memberlsp in lspBW:
	 logging.info("Member-LSP %s -- maxavgBW %s, signalBW %s",memberlsp.name, memberlsp.max_avg_bandwidth, memberlsp.signal_bandwidth)
	 sumlspavgBW = sumlspavgBW + get_bps(memberlsp.max_avg_bandwidth)
	 sumlspsignalBW = sumlspsignalBW + get_bps(memberlsp.signal_bandwidth)

	 memberlsp_max_avg_bw_json_body = [{
	 "name": memberlsp.name + " LSP MaxAvg BW",
	 "columns": ["value"],
	 "points": [[get_bps(memberlsp.max_avg_bandwidth)]],
	 }]
	 db.write_points(memberlsp_max_avg_bw_json_body,time_precision='s')

	 memberlsp_signal_bw_json_body = [{
	 "name": memberlsp.name + " LSP Signalled BW",
	 "columns": ["value"],
	 "points": [[get_bps(memberlsp.signal_bandwidth)]],
	 }]
	 db.write_points(memberlsp_signal_bw_json_body,time_precision='s')

	# Writing stats and json for sum of all member LSPs stats
	logging.info("All member LSPs -- maxavgBW %s, signalBW %s",sumlspavgBW, sumlspsignalBW)
	sumlsp_avgBW_json_body = [{
	 "name": "All member LSP MaxAvg BW",
	 "columns": ["value"],
	 "points": [[sumlspavgBW]],
	 }]
	db.write_points(sumlsp_avgBW_json_body,time_precision='s')
	sumlsp_signalBW_json_body = [{
	 "name": "All member LSP Signalled BW",
	 "columns": ["value"],
	 "points": [[sumlspsignalBW]],
	 }]
	db.write_points(sumlsp_signalBW_json_body,time_precision='s')


# Function with RPC to obtain aggregate BW 

def get_aggr_lsp_bw (yamlfile,dev,db):

	# RPC to obtain container-lsp stats
	aggrlspbw = loadyaml(yamlfile)
	globals().update(aggrlspbw)
	containerBW = MemberLSPAggrBWTable(dev)
	containerBW.get()

	for lsp in containerBW:
		logging.info("Container-LSP %s-- aggregBW %s, currentBW %s",lsp.name, lsp.aggregate_bandwidth, lsp.current_bandwidth)
		lsp_aggrbw_json_body = [{
		"name": lsp.name + " LSP Aggregate BW",
		"columns": ["value"],
		"points": [[get_bps(lsp.aggregate_bandwidth)]],
		}]
		db.write_points(lsp_aggrbw_json_body,time_precision='s')
		lsp_current_bw_json_body = [{
		"name": lsp.name + " LSP Current BW",
		"columns": ["value"],
		"points": [[get_bps(lsp.current_bandwidth)]],
		}]
		db.write_points(lsp_current_bw_json_body,time_precision='s')

# Function with RPC to obtain member-lsps stats 

def get_input_ifl_stats (inputifl,dev,db):

	inputiflstats = dev.rpc.get_interface_information(extensive=True, interface_name=inputifl)
	inputiflbytes = int(inputiflstats.findtext('logical-interface/transit-traffic-statistics/input-bytes'))
	inputiflbps = int(inputiflstats.findtext('logical-interface/transit-traffic-statistics/input-bps'))
	inputiflpackets = int(inputiflstats.findtext('logical-interface/transit-traffic-statistics/input-packets'))
	inputiflpps = int(inputiflstats.findtext('logical-interface/transit-traffic-statistics/input-pps'))

	logging.info("Input ifl stats -- packets %s, pps %s, bytes %s, bps %s",inputiflpackets, inputiflpps, inputiflbytes, inputiflbps)

	input_ifl_bytes_json_body = [{
	 "name": "Input ifl bytes",
	 "columns": ["value"],
	 "points": [[inputiflbytes]],
	 }]
	db.write_points(input_ifl_bytes_json_body,time_precision='s')

	input_ifl_bps_json_body = [{
	 "name": "Input ifl bps",
	 "columns": ["value"],
	 "points": [[inputiflbps]],
	 }]
	db.write_points(input_ifl_bps_json_body,time_precision='s')

	input_ifl_packets_json_body = [{
	 "name": "Input ifl packets",
	 "columns": ["value"],
	 "points": [[inputiflpackets]],
	 }]
	db.write_points(input_ifl_packets_json_body,time_precision='s')

	input_ifl_pps_json_body = [{
	 "name": "Input ifl pps",
	 "columns": ["value"],
	 "points": [[inputiflpps]],
	 }]
	db.write_points(input_ifl_pps_json_body,time_precision='s')

#################################################

parse = argparse.ArgumentParser(description='Extract TE++ details according to duration and interval')

parse.add_argument('-duration', '--duration', required=False, default='60', dest='duration', help='test duration in minutes')

parse.add_argument('-interval', '--interval', required=False, default='30', dest='interval', help='data scan interval in seconds')

#################################################

# Main function
def main ():
	
	#################################################
	# Set logging level 
	logging.basicConfig(level=logging.INFO)

	#################################################
	# Parsing arguments or inheriting default values

	args = parse.parse_args()
	durationtime = int(args.duration)*60
	interval = int(args.interval)
	logging.error('---- Starting test for %s minutes, scanning data every %s seconds',int(args.duration),interval)

	#################################################

	#Initialize InfluxDB and return value
	try:
		db_name = 'db1'
		clientdb = InfluxDBClient('127.0.0.1', 8086, 'root', 'root',db_name)
		all_dbs_list = clientdb.get_list_database()
		# That list comes back like: [{u'name': u'dbname'}]
		if db_name not in [str(x['name']) for x in all_dbs_list]:
		    logging.info("---- Creating db %s",format(db_name))
		    clientdb.create_database(db_name)
		else:
		    logging.info("---- Reusing db %s",format(db_name))
		    clientdb.delete_database(db_name)
		    clientdb.create_database(db_name)
	except:
		logging.error('InfluxDB initialization failure!!!')
		sys.exit('---- Could not create InfluxDB at DUT: [NOK]')

	#################################################

	# Opening connection to DUT 
	dev = Device(host='localhost.localdomain', port=8002, user='gonzalo')

	try:
	    dev.open()
	    logging.info('---- Connection to DUT: [OK]')
	    
	except Exception as err:
		logging.error('!!! DUT connection failure due to', err)
		sys.exit('---- Could not connect to DUT: [NOK]')

	#################################################
	
	# Initialize container-LSP, clear all stats
	try:
		# Create InlfuxDB and initialize everything
	 	initialize('Jaen-to-Soria-DYN-AUTOBW-TE++',dev)
	 	logging.info('---- Initializing DUT stats and creating InfluxDB: [OK]')

	except:
		logging.error('DUT initialization failure!!!')
		sys.exit('---- Could not initialize stats at DUT: [NOK]')

	#################################################
	
	# Initialize iteration counter
	i = 1

	# Set final test timestamp
	finaltimestamp = int(time.time()) + durationtime

	while (int(time.time())<=finaltimestamp):
		logging.info("###############  Test interation %s ############### ",i)
		i = i+1
		localsystemtime = dev.rpc.get_system_uptime_information()
		logging.info("//// DUT timestamp:  %s ////",localsystemtime.findtext('current-time/date-time'))
		get_member_lsp_summary ('Jaen-to-Soria-DYN-AUTOBW-TE++',dev,clientdb)
		get_member_lsp_stats ('show-member-lsp-stats.yml',dev,clientdb)
		get_member_lsp_bw ('show-member-lsp-bw.yml',dev,clientdb)
		get_aggr_lsp_bw ('show-container-lsp-bw.yml',dev,clientdb)
		get_input_ifl_stats ('xe-0/0/0.1020',dev,clientdb)
		time.sleep(interval)


	#################################################

	# Closing connection to DUT 

	logging.info('Closing connection to DUT')

	try:
	    dev.close()
	    logging.info('---- Disconnection from DUT: [OK]')
	    
	except Exception as err:
		# Abort existing connections
		test_ixnet_disconnect(ixNet)

		logging.error('DUT connection closure failure due to', err)
		sys.exit('---- Could not disconnect from DUT: [NOK]')

	#################################################

	# End of Test 

	logging.info('++++ End of Test ++++')

#################################################
#################################################

# Invoking main function

if __name__ == "__main__":
    try:
    	main()
    	logging.info('///////////////////////// END ///////////////////////////////')
    except Exception:
    	logging.info('///////////////////////// EXIT !!! //////////////////////////')
    	raise
    except SystemExit as exit:
    	logging.error(exit)
    	logging.info('///////////////////////// EXIT !!! //////////////////////////')
    	pass


