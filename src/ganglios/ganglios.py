
"""
@file ganglios.py
@brief utilities to make ganglios checks (nagios plugins) less ugly

Copyright (c) 2007, Linden Research, Inc.
License to use, modify, and distribute under the GPLv2 or later
http://www.gnu.org/licenses/gpl-2.0.html

There are two ways to use this module.
a) examine *all* hosts for a given metric and analyze them using a callback function
b) examine a *single* host for a specific metric and return that metric
(a) is appropriate if you want to be notified if any host crosses a certain
  threshold.  It is more efficient than creating a nagios check for every host on
  that metric.  An example would be checking to see if any host has >95% disk
  space used.  To set this up, create a 'ganglia' host in the nagios config and
  put the service checks under that host.  Note that you won't be able to resolve
  the nagios alert until *all* hosts are back below the threshold.  This can lead
  to alerts just hanging out on your nagios page for too long.
(b) is appropriate to check a specific host for a condition.  If you have 1000
  hosts, of which 20 are web servers, you should use this method to test your web
  servers for Stuff so as to avoid wasting cycles for the other 980 hosts.
"""

import os
import sys
import time
import stat
import glob
import socket

import xml.etree.ElementTree as ET
import xml.parsers.expat as expat

__revision__ = '0'

_cachedir = '/var/lib/ganglia/xmlcache/'
_stale_time = 300
_hostdir = os.path.join(_cachedir, 'hosts')

def parse_ganglia (metrics, thunk):
    """
    metrics is a list of strings.
    thunk is a callback.

    This parses the xml files in /tmp/ganglia-cache/ and calls thunk
    every time a METRIC with NAME in metrics is seen.  Use this function for
    method (a) above

    thunk should take 3 arguments: (host-name, metric-name, value)
    """
    status = 0 # ok
    bad = []

    # go_bad collects xml cache files that are old, broken or otherwise
    # unparseable and stops us from parsing them again in the future
    def go_bad (xml_file, bad):
        """ change status to bad, and output the stale nannybot """
        bad_host = xml_file.replace ('.xml', '')
        if not bad_host in bad:
            bad += [bad_host]

    try:
        os.mkdir(_cachedir)
    except:
        pass

    for xml_file in os.listdir(_cachedir):
        filename = _cachedir+xml_file
        if xml_file.endswith ('.xml'):
            # make sure the data is fresh
            mod_time = os.stat (filename)[stat.ST_MTIME]
            if time.time () - mod_time > _stale_time:
                go_bad (xml_file, bad)
                status = 2
            # read the xml file, look for certain metrics
            f_hndl = open (filename)
            try:
                tree = ET.parse (f_hndl)
                root = tree.getroot()
                clusters = list(root)
                for cluster in clusters:
                    for host in cluster.findall('HOST'):
                        for metric in host.findall('METRIC'):
                            if metric.attrib['NAME'] in metrics:
                                try:
                                    thunk( host.attrib['NAME'],
                                        metric.attrib['NAME'],
                                        metric.attrib['VAL'])
                                except Exception, e:
                                    print "thunk threw an exception: %s" % e
                                    raise
            except expat.ExpatError:
                go_bad (xml_file, bad)
                status = 2
            f_hndl.close ()
    if len (bad) > 0:
        if status == 0:
            status = 2 # critical
        sys.stdout.write ('<b>STALE</b>:')
        for bad_host in bad:
            sys.stdout.write (bad_host + ' ')
    return status

def get_metric_for_host(hostname, metricname):
    """
    using the new-style (one file per host), this 
    takes a hostname, looks up the metric, and returns its value
    This is method (b) above
    """

    # first, find the canonical name for the host passed in
    # i.e. translate inv5-mysql.agni.lindenlab.com to db1c3.lindenlab.com
    try:
        new_hostname = socket.gethostbyaddr(hostname)[0]
    except socket.gaierror, e:
        # name not found.  it will probably fail anyways... but pass it through just in case
        new_hostname = hostname
    hostname = new_hostname

    #strip off leading int., eth0., etc.
    split_name = hostname.split('.')
    if(split_name[0] in ('int', 'eth0', 'eth1', 'tunnel0', 'tunnel1')):
        hostname = '.'.join(split_name[1:])

    # find the one file that best matches what came in.  checks for names like
    # int.$name and $name and complains if it doesn't find a unique match.
    filelist = glob.glob(os.path.join(_hostdir, "*.%s" % hostname))
    if len(filelist) == 0:
        filelist = glob.glob(os.path.join(_hostdir, "%s" % hostname))
    # if there's still no match, complain host not found.
    if len(filelist) == 0:
        raise Exception("Host not found: %s." % hostname)
###
###  for the VPNs, it's a valid state that there exist >1 files for each vpn 
###  (a tunnel address and a private interface).  What's the right action to take
###  here?  not sure...  -green 2008-05-28
###
#    if len(filelist) != 1:
#        sys.stdout.write("not exactly one match for '%s' (found %s)" % (hostname, len(filelist)))
#        done(2)

    filename = filelist[0]    # there can be only one
    # make sure it's not old data
    mod_time = os.stat(filename)[stat.ST_MTIME]
    if time.time () - mod_time > _stale_time:   # seconds
        sys.stdout.write('STALE')
        done(2)

    # read the xml file, look for certain metrics
    f_hndl = open(filename)
    try:
        tree = ET.parse (f_hndl)
        for metric in tree.findall('METRIC'):
            # found a metric we care about.
            if metric.attrib['NAME'] == metricname:
                return metric.attrib['VAL']
    except expat.ExpatError:
        sys.stdout.write("XML parse error")
        done(2)
    f_hndl.close()



def done (status):
    """ print newline if needed, exit with status """
    print ''
    sys.exit (status)
