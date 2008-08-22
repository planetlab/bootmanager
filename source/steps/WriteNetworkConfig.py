#!/usr/bin/python2
# $Id$
#
# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.
# expected /proc/partitions format

import os, string
import traceback

import utils
import urlparse
import httplib

from Exceptions import *
import BootServerRequest
import ModelOptions
import BootAPI

def Run( vars, log ):
    """
    Write out the network configuration for this machine:
    /etc/hosts
    /etc/sysconfig/network-scripts/ifcfg-<ifname>
    /etc/resolv.conf (if applicable)
    /etc/sysconfig/network

    The values to be used for the network settings are to be set in vars
    in the variable 'INTERFACE_SETTINGS', which is a dictionary
    with keys:

     Key               Used by this function
     -----------------------------------------------
     node_id
     node_key
     method            x
     ip                x
     mac               x (optional)
     gateway           x
     network           x
     broadcast         x
     netmask           x
     dns1              x
     dns2              x (optional)
     hostname          x
     domainname        x

    Expect the following variables from the store:
    SYSIMG_PATH             the path where the system image will be mounted
                                (always starts with TEMP_PATH)
    INTERFACES              All the interfaces associated with this node
    INTERFACE_SETTINGS      dictionary 
    Sets the following variables:
    None
    """

    log.write( "\n\nStep: Install: Writing Network Configuration files.\n" )

    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    try:
        interface_settings= vars['INTERFACE_SETTINGS']
    except KeyError, e:
        raise BootManagerException, "No interface settings found in vars."

    try:
        hostname= interface_settings['hostname']
        domainname= interface_settings['domainname']
        method= interface_settings['method']
        ip= interface_settings['ip']
        gateway= interface_settings['gateway']
        network= interface_settings['network']
        netmask= interface_settings['netmask']
        dns1= interface_settings['dns1']
        mac= interface_settings['mac']
    except KeyError, e:
        raise BootManagerException, "Missing value %s in interface settings." % str(e)

    try:
        dns2= ''
        dns2= interface_settings['dns2']
    except KeyError, e:
        pass


    # Node Manager needs at least PLC_API_HOST and PLC_BOOT_HOST
    log.write("Writing /etc/planetlab/plc_config\n")
    utils.makedirs("%s/etc/planetlab" % SYSIMG_PATH)
    plc_config = file("%s/etc/planetlab/plc_config" % SYSIMG_PATH, "w")

    api_url = vars['BOOT_API_SERVER']
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(api_url)
    parts = netloc.split(':')
    host = parts[0]
    if len(parts) > 1:
        port = parts[1]
    else:
        port = '80'
    try:
        log.write("getting via https://%s/PlanetLabConf/get_plc_config.php " % host)
        bootserver = httplib.HTTPSConnection(host, port)
        bootserver.connect()
        bootserver.request("GET","https://%s/PlanetLabConf/get_plc_config.php" % host)
        plc_config.write("%s" % bootserver.getresponse().read())
        bootserver.close()
        log.write("Done\n")
    except :
        log.write(" .. Failed.  Using old method. -- stack trace follows\n")
        traceback.print_exc(file=log.OutputFile)
        bs= BootServerRequest.BootServerRequest()
        if bs.BOOTSERVER_CERTS:
            print >> plc_config, "PLC_BOOT_HOST='%s'" % bs.BOOTSERVER_CERTS.keys()[0]
        print >> plc_config, "PLC_API_HOST='%s'" % host
        print >> plc_config, "PLC_API_PORT='%s'" % port
        print >> plc_config, "PLC_API_PATH='%s'" % path

    plc_config.close()


    log.write( "Writing /etc/hosts\n" )
    hosts_file= file("%s/etc/hosts" % SYSIMG_PATH, "w" )    
    hosts_file.write( "127.0.0.1       localhost\n" )
    if method == "static":
        hosts_file.write( "%s %s.%s\n" % (ip, hostname, domainname) )
    hosts_file.close()
    hosts_file= None
    

    if method == "static":
        log.write( "Writing /etc/resolv.conf\n" )
        resolv_file= file("%s/etc/resolv.conf" % SYSIMG_PATH, "w" )
        if dns1 != "":
            resolv_file.write( "nameserver %s\n" % dns1 )
        if dns2 != "":
            resolv_file.write( "nameserver %s\n" % dns2 )
        resolv_file.write( "search %s\n" % domainname )
        resolv_file.close()
        resolv_file= None

    log.write( "Writing /etc/sysconfig/network\n" )
    network_file= file("%s/etc/sysconfig/network" % SYSIMG_PATH, "w" )
    network_file.write( "NETWORKING=yes\n" )
    network_file.write( "HOSTNAME=%s.%s\n" % (hostname, domainname) )
    if method == "static":
        network_file.write( "GATEWAY=%s\n" % gateway )
    network_file.close()
    network_file= None

    interfaces = {}
    interface_count = 1
    for interface in vars['INTERFACES']:
        if method == "static" or method == "dhcp":
            if interface['is_primary'] == 1:
                ifnum = 0
            else:
                ifnum = interface_count
                interface_count += 1

            int = {}
            if interface['mac']:
                int['HWADDR'] = interface['mac']

            if interface['method'] == "static":
                int['BOOTPROTO'] = "static"
                int['IPADDR'] = interface['ip']
                int['NETMASK'] = interface['netmask']

            elif interface['method'] == "dhcp":
                int['BOOTPROTO'] = "dhcp"
                if interface['hostname']:
                    int['DHCP_HOSTNAME'] = interface['hostname']
                else:
                    int['DHCP_HOSTNAME'] = hostname
                if not interface['is_primary']:
                    int['DHCLIENTARGS'] = "-R subnet-mask"

            alias = ""
            ifname=None
            if len(interface['interface_setting_ids']) > 0:
                settings = \
                    BootAPI.call_api_function(vars, "GetInterfaceSettings",
                                              ({'interface_setting_id': 
                                                interface['interface_setting_ids']},))
                for setting in settings:
                    # to explicitly set interface name
                    if   setting['name'].upper() == "IFNAME":
                        ifname=setting['value']
                    elif setting['name'].upper() == "DRIVER":
                        # xxx not sure how to do that yet - probably add a line in modprobe.conf
                        pass
                    elif setting['name'].upper() == "ALIAS":
                        alias = ":" + setting['value']

                    # a hack for testing before a new setting is hardcoded here
                    # use the backdoor setting and put as a value 'var=value'
                    elif setting['name'].upper() == "BACKDOOR":
                        [var,value]=setting['value'].split('=',1)
                        int[var]=value

                    elif setting['name'].lower() in \
                            [  "mode", "essid", "nw", "freq", "channel", "sens", "rate",
                               "key", "key1", "key2", "key3", "key4", "securitymode", 
                               "iwconfig", "iwpriv" ] :
                        int [setting['name'].upper()] = setting['value']
                        int ['TYPE']='Wireless'
                    else:
                        log.write("Warning - ignored setting named %s\n"%setting['name'])

            if alias and 'HWADDR' in int:
                for (dev, i) in interfaces.iteritems():
                    if i['HWADDR'] == int['HWADDR']:
                        break
                del int['HWADDR']
                interfaces[dev + alias] = int
                interface_count -= 1
            else:
                if not ifname:
                    ifname="eth%d" % ifnum
                else:
                    interface_count -= 1
                interfaces[ifname] = int

    for (dev, int) in interfaces.iteritems():
        path = "%s/etc/sysconfig/network-scripts/ifcfg-%s" % (
               SYSIMG_PATH, dev)
        f = file(path, "w")
        log.write("Writing %s\n" % path.replace(SYSIMG_PATH, ""))

        f.write("DEVICE=%s\n" % dev)
        f.write("ONBOOT=yes\n")
        f.write("USERCTL=no\n")
        for (key, val) in int.iteritems():
            f.write('%s="%s"\n' % (key, val))

        f.close()

