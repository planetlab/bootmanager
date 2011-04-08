#!/usr/bin/python
#
# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.
# expected /proc/partitions format

import sys, os, traceback
import string
import socket
import re

import utils
from Exceptions import *
import BootServerRequest
import BootAPI
import notify_messages
import UpdateRunLevelWithPLC


# two possible names of the configuration files
NEW_CONF_FILE_NAME= "plnode.txt"
OLD_CONF_FILE_NAME= "planet.cnf"


def Run( vars, log ):   
    """
    read the machines node configuration file, which contains
    the node key and the node_id for this machine.
    
    these files can exist in several different locations with
    several different names. Below is the search order:

    filename      floppy   flash    ramdisk    cd
    plnode.txt      1        2      4 (/)      5 (/usr/boot), 6 (/usr)
    planet.cnf      3

    The locations will be searched in the above order, plnode.txt
    will be checked first, then planet.cnf. Flash devices will only
    be searched on 3.0 cds.

    Because some of the earlier
    boot cds don't validate the configuration file (which results
    in a file named /tmp/planet-clean.cnf), and some do, lets
    bypass this, and mount and attempt to read in the conf
    file ourselves. If it doesn't exist, we cannot continue, and a
    BootManagerException will be raised. If the configuration file is found
    and read, return 1.

    Expect the following variables from the store:
    
    Sets the following variables from the configuration file:
    WAS_NODE_ID_IN_CONF         Set to 1 if the node id was in the conf file
    WAS_NODE_KEY_IN_CONF         Set to 1 if the node key was in the conf file
    NONE_ID                     The db node_id for this machine
    NODE_KEY                    The key for this node
    INTERFACE_SETTINGS            A dictionary of the values from the network
                                configuration file. keys set:
                                   method               IP_METHOD
                                   ip                   IP_ADDRESS
                                   mac                  NET_DEVICE       
                                   gateway              IP_GATEWAY
                                   network              IP_NETADDR
                                   broadcast            IP_BROADCASTADDR
                                   netmask              IP_NETMASK
                                   dns1                 IP_DNS1
                                   dns2                 IP_DNS2
                                   hostname             HOST_NAME
                                   domainname           DOMAIN_NAME
                                -- wlan oriented --
                                   ssid                 WLAN_SSID
                                   iwconfig             WLAN_IWCONFIG

    the mac address is read from the machine unless it exists in the
    configuration file.
    """

    log.write( "\n\nStep: Reading node configuration file.\n" )


    # make sure we have the variables we need

    INTERFACE_SETTINGS= {}
    INTERFACE_SETTINGS['method']= "dhcp"
    INTERFACE_SETTINGS['ip']= ""
    INTERFACE_SETTINGS['mac']= ""
    INTERFACE_SETTINGS['gateway']= ""
    INTERFACE_SETTINGS['network']= ""
    INTERFACE_SETTINGS['broadcast']= ""
    INTERFACE_SETTINGS['netmask']= ""
    INTERFACE_SETTINGS['dns1']= ""
    INTERFACE_SETTINGS['dns2']= ""
    INTERFACE_SETTINGS['hostname']= "localhost"
    INTERFACE_SETTINGS['domainname']= "localdomain"
    vars['INTERFACE_SETTINGS']= INTERFACE_SETTINGS

    vars['NODE_ID']= 0
    vars['NODE_KEY']= ""

    vars['WAS_NODE_ID_IN_CONF']= 0
    vars['WAS_NODE_KEY_IN_CONF']= 0

    vars['DISCONNECTED_OPERATION']= ''

    # for any devices that need to be mounted to get the configuration
    # file, mount them here.
    mount_point= "/tmp/conffilemount"
    utils.makedirs( mount_point )

    old_conf_file_contents= None
    conf_file_contents= None
    
    
    # 1. check the regular floppy device
    log.write( "Checking standard floppy disk for plnode.txt file.\n" )

    log.write( "Mounting /dev/fd0 on %s\n" % mount_point )
    utils.sysexec_noerr( "mount -o ro -t ext2,msdos /dev/fd0 %s " \
                         % mount_point, log )

    conf_file_path= "%s/%s" % (mount_point,NEW_CONF_FILE_NAME)
    
    log.write( "Checking for existence of %s\n" % conf_file_path )
    if os.access( conf_file_path, os.R_OK ):
        try:
            conf_file= file(conf_file_path,"r")
            conf_file_contents= conf_file.read()
            conf_file.close()
            log.write( "Read in contents of file %s\n" % conf_file_path )
        except IOError, e:
            log.write( "Unable to read file %s\n" % conf_file_path )
            pass

        utils.sysexec_noerr( "umount %s" % mount_point, log )
        if __parse_configuration_file( vars, log, conf_file_contents):
            return 1
        else:
            raise BootManagerException( "Found configuration file plnode.txt " \
                                        "on floppy, but was unable to parse it." )


    # try the old file name, same device. its actually number 3 on the search
    # order, but do it now to save mounting/unmounting the disk twice.
    # try to parse it later...
    conf_file_path= "%s/%s" % (mount_point,OLD_CONF_FILE_NAME)

    log.write( "Checking for existence of %s (used later)\n" % conf_file_path )
    if os.access( conf_file_path, os.R_OK ):
        try:
            old_conf_file= file(conf_file_path,"r")
            old_conf_file_contents= old_conf_file.read()
            old_conf_file.close()
            log.write( "Read in contents of file %s\n" % conf_file_path )
        except IOError, e:
            log.write( "Unable to read file %s\n" % conf_file_path )
            pass
        
    utils.sysexec_noerr( "umount %s" % mount_point, log )

    # 2. check flash devices on 3.0 based cds
    log.write( "Checking flash devices for plnode.txt file.\n" )

    # this is done the same way the 3.0 cds do it, by attempting
    # to mount and sd*1 devices that are removable
    devices= os.listdir("/sys/block/")

    for device in devices:
        if device[:2] != "sd":
            log.write( "Skipping non-scsi device %s\n" % device )
            continue

        # test removable
        removable_file_path= "/sys/block/%s/removable" % device
        try:
            removable= int(file(removable_file_path,"r").read().strip())
        except ValueError, e:
            continue
        except IOError, e:
            continue

        if not removable:
            log.write( "Skipping non-removable device %s\n" % device )
            continue

        log.write( "Checking removable device %s\n" % device )

        partitions= file("/proc/partitions", "r")
        for line in partitions:
            found_file= 0
            parsed_file= 0
            
            if not re.search("%s[0-9]*$" % device, line):
                continue

            try:
                # major minor  #blocks  name
                parts= string.split(line)

                # ok, try to mount it and see if we have a conf file.
                full_device= "/dev/%s" % parts[3]
            except IndexError, e:
                log.write( "Incorrect /proc/partitions line:\n%s\n" % line )
                continue

            log.write( "Mounting %s on %s\n" % (full_device,mount_point) )
            try:
                utils.sysexec( "mount -o ro -t ext2,msdos %s %s" \
                               % (full_device,mount_point), log )
            except BootManagerException, e:
                log.write( "Unable to mount, trying next partition\n" )
                continue

            conf_file_path= "%s/%s" % (mount_point,NEW_CONF_FILE_NAME)

            log.write( "Checking for existence of %s\n" % conf_file_path )
            if os.access( conf_file_path, os.R_OK ):
                try:
                    conf_file= file(conf_file_path,"r")
                    conf_file_contents= conf_file.read()
                    conf_file.close()
                    found_file= 1
                    log.write( "Read in contents of file %s\n" % \
                               conf_file_path )

                    if __parse_configuration_file( vars, log, \
                                                   conf_file_contents):
                        parsed_file= 1
                except IOError, e:
                    log.write( "Unable to read file %s\n" % conf_file_path )

            utils.sysexec_noerr( "umount %s" % mount_point, log )
            if found_file:
                if parsed_file:
                    return 1
                else:
                    raise BootManagerException( \
                        "Found configuration file plnode.txt " \
                        "on floppy, but was unable to parse it.")


            
    # 3. check standard floppy disk for old file name planet.cnf
    log.write( "Checking standard floppy disk for planet.cnf file " \
               "(for legacy nodes).\n" )

    if old_conf_file_contents:
        if __parse_configuration_file( vars, log, old_conf_file_contents):
            return 1
        else:
            raise BootManagerException( "Found configuration file planet.cnf " \
                                        "on floppy, but was unable to parse it." )


    # 4. check for plnode.txt in / (ramdisk)
    log.write( "Checking / (ramdisk) for plnode.txt file.\n" )
    
    conf_file_path= "/%s" % NEW_CONF_FILE_NAME

    log.write( "Checking for existence of %s\n" % conf_file_path )
    if os.access(conf_file_path,os.R_OK):
        try:
            conf_file= file(conf_file_path,"r")
            conf_file_contents= conf_file.read()
            conf_file.close()
            log.write( "Read in contents of file %s\n" % conf_file_path )
        except IOError, e:
            log.write( "Unable to read file %s\n" % conf_file_path )
            pass
    
        if __parse_configuration_file( vars, log, conf_file_contents):            
            return 1
        else:
            raise BootManagerException( "Found configuration file plnode.txt " \
                                        "in /, but was unable to parse it.")

    
    # 5. check for plnode.txt in /usr/boot (mounted already)
    log.write( "Checking /usr/boot (cd) for plnode.txt file.\n" )
    
    conf_file_path= "/usr/boot/%s" % NEW_CONF_FILE_NAME

    log.write( "Checking for existence of %s\n" % conf_file_path )
    if os.access(conf_file_path,os.R_OK):
        try:
            conf_file= file(conf_file_path,"r")
            conf_file_contents= conf_file.read()
            conf_file.close()
            log.write( "Read in contents of file %s\n" % conf_file_path )
        except IOError, e:
            log.write( "Unable to read file %s\n" % conf_file_path )
            pass
    
        if __parse_configuration_file( vars, log, conf_file_contents):            
            return 1
        else:
            raise BootManagerException( "Found configuration file plnode.txt " \
                                        "in /usr/boot, but was unable to parse it.")



    # 6. check for plnode.txt in /usr (mounted already)
    log.write( "Checking /usr (cd) for plnode.txt file.\n" )
    
    conf_file_path= "/usr/%s" % NEW_CONF_FILE_NAME

    log.write( "Checking for existence of %s\n" % conf_file_path )
    if os.access(conf_file_path,os.R_OK):
        try:
            conf_file= file(conf_file_path,"r")
            conf_file_contents= conf_file.read()
            conf_file.close()
            log.write( "Read in contents of file %s\n" % conf_file_path )
        except IOError, e:
            log.write( "Unable to read file %s\n" % conf_file_path )
            pass    
    
        if __parse_configuration_file( vars, log, conf_file_contents):            
            return 1
        else:
            raise BootManagerException( "Found configuration file plnode.txt " \
                                        "in /usr, but was unable to parse it.")


    raise BootManagerException, "Unable to find and read a node configuration file."
    



def __parse_configuration_file( vars, log, file_contents ):
    """
    parse a configuration file, set keys in var INTERFACE_SETTINGS
    in vars (see comment for function ReadNodeConfiguration). this
    also reads the mac address from the machine if successful parsing
    of the configuration file is completed.
    """

    INTERFACE_SETTINGS= vars["INTERFACE_SETTINGS"]
    
    if file_contents is None:
        log.write( "__parse_configuration_file called with no file contents\n" )
        return 0
    
    try:
        line_num= 0
        for line in file_contents.split("\n"):

            line_num = line_num + 1
            
            # if its a comment or a whitespace line, ignore
            if line[:1] == "#" or string.strip(line) == "":
                continue

            # file is setup as name="value" pairs
            parts= string.split(line, "=", 1)

            name= string.strip(parts[0])
            value= string.strip(parts[1])

            # make sure value starts and ends with
            # single or double quotes
            quotes= value[0] + value[len(value)-1]
            if quotes != "''" and quotes != '""':
                log.write( "Invalid line %d in configuration file:\n" % line_num )
                log.write( line + "\n" )
                return 0

            # get rid of the quotes around the value
            value= string.strip(value[1:len(value)-1])

            if name == "NODE_ID":
                try:
                    vars['NODE_ID']= int(value)
                    vars['WAS_NODE_ID_IN_CONF']= 1
                except ValueError, e:
                    log.write( "Non-numeric node_id in configuration file.\n" )
                    return 0

            if name == "NODE_KEY":
                vars['NODE_KEY']= value
                vars['WAS_NODE_KEY_IN_CONF']= 1

            if name == "IP_METHOD":
                value= string.lower(value)
                if value != "static" and value != "dhcp":
                    log.write( "Invalid IP_METHOD in configuration file:\n" )
                    log.write( line + "\n" )
                    return 0
                INTERFACE_SETTINGS['method']= value.strip()

            if name == "IP_ADDRESS":
                INTERFACE_SETTINGS['ip']= value.strip()

            if name == "IP_GATEWAY":
                INTERFACE_SETTINGS['gateway']= value.strip()

            if name == "IP_NETMASK":
                INTERFACE_SETTINGS['netmask']= value.strip()

            if name == "IP_NETADDR":
                INTERFACE_SETTINGS['network']= value.strip()

            if name == "IP_BROADCASTADDR":
                INTERFACE_SETTINGS['broadcast']= value.strip()

            if name == "IP_DNS1":
                INTERFACE_SETTINGS['dns1']= value.strip()

            if name == "IP_DNS2":
                INTERFACE_SETTINGS['dns2']= value.strip()

            if name == "HOST_NAME":
                INTERFACE_SETTINGS['hostname']= string.lower(value)

            if name == "DOMAIN_NAME":
                INTERFACE_SETTINGS['domainname']= string.lower(value)

            if name == "NET_DEVICE":
                INTERFACE_SETTINGS['mac']= string.upper(value)

            if name == "DISCONNECTED_OPERATION":
                vars['DISCONNECTED_OPERATION']= value.strip()

    except IndexError, e:
        log.write( "Unable to parse configuration file\n" )
        return 0

    # now if we are set to dhcp, clear out any fields
    # that don't make sense
    if INTERFACE_SETTINGS["method"] == "dhcp":
        INTERFACE_SETTINGS["ip"]= ""
        INTERFACE_SETTINGS["gateway"]= ""     
        INTERFACE_SETTINGS["netmask"]= ""
        INTERFACE_SETTINGS["network"]= ""
        INTERFACE_SETTINGS["broadcast"]= ""
        INTERFACE_SETTINGS["dns1"]= ""
        INTERFACE_SETTINGS["dns2"]= ""

    log.write("Successfully read and parsed node configuration file.\n" )

    # if the mac wasn't specified, read it in from the system.
    if INTERFACE_SETTINGS["mac"] == "":
        device= "eth0"
        mac_addr= utils.get_mac_from_interface(device)

        if mac_addr is None:
            log.write( "Could not get mac address for device eth0.\n" )
            return 0

        INTERFACE_SETTINGS["mac"]= string.upper(mac_addr)

        log.write( "Got mac address %s for device %s\n" %
                   (INTERFACE_SETTINGS["mac"],device) )
        

    # now, if the conf file didn't contain a node id, post the mac address
    # to plc to get the node_id value
    if vars['NODE_ID'] is None or vars['NODE_ID'] == 0:
        log.write( "Configuration file does not contain the node_id value.\n" )
        log.write( "Querying PLC for node_id.\n" )

        bs_request= BootServerRequest.BootServerRequest(vars)
        
        postVars= {"mac_addr" : INTERFACE_SETTINGS["mac"]}
        result= bs_request.DownloadFile( "/boot/getnodeid.php",
                                         None, postVars, 1, 1,
                                         "/tmp/node_id")
        if result == 0:
            log.write( "Unable to make request to get node_id.\n" )
            return 0

        try:
            node_id_file= file("/tmp/node_id","r")
            node_id= string.strip(node_id_file.read())
            node_id_file.close()
        except IOError:
            log.write( "Unable to read node_id from /tmp/node_id\n" )
            return 0

        try:
            node_id= int(string.strip(node_id))
        except ValueError:
            log.write( "Got node_id from PLC, but not numeric: %s" % str(node_id) )
            return 0

        if node_id == -1:
            log.write( "Got node_id, but it returned -1\n\n" )

            log.write( "------------------------------------------------------\n" )
            log.write( "This indicates that this node could not be identified\n" )
            log.write( "by PLC. You will need to add the node to your site,\n" )
            log.write( "and regenerate the network configuration file.\n" )
            log.write( "See the Technical Contact guide for node setup\n" )
            log.write( "procedures.\n\n" )
            log.write( "Boot process canceled until this is completed.\n" )
            log.write( "------------------------------------------------------\n" )
            
            cancel_boot_flag= "/tmp/CANCEL_BOOT"
            # this will make the initial script stop requesting scripts from PLC
            utils.sysexec( "touch %s" % cancel_boot_flag, log )

            return 0

        log.write( "Got node_id from PLC: %s\n" % str(node_id) )
        vars['NODE_ID']= node_id



    if vars['NODE_KEY'] is None or vars['NODE_KEY'] == "":
        log.write( "Configuration file does not contain a node_key value.\n" )
        log.write( "Using boot nonce instead.\n" )

        # 3.x cds stored the file in /tmp/nonce in ascii form, so they
        # can be read and used directly. 2.x cds stored in the same place
        # but in binary form, so we need to convert it to ascii the same
        # way the old boot scripts did so it matches whats in the db
        # (php uses bin2hex, 
        read_mode= "r"
            
        try:
            nonce_file= file("/tmp/nonce",read_mode)
            nonce= nonce_file.read()
            nonce_file.close()
        except IOError:
            log.write( "Unable to read nonce from /tmp/nonce\n" )
            return 0

        nonce= string.strip(nonce)

        log.write( "Read nonce, using as key.\n" )
        vars['NODE_KEY']= nonce
        
        
    # at this point, we've read the network configuration file.
    # if we were setup using dhcp, get this system's current ip
    # address and update the vars key ip, because it
    # is needed for future api calls.

    # at the same time, we can check to make sure that the hostname
    # in the configuration file matches the ip address. if it fails
    # notify the owners

    hostname= INTERFACE_SETTINGS['hostname'] + "." + \
              INTERFACE_SETTINGS['domainname']

    # set to 0 if any part of the hostname resolution check fails
    hostname_resolve_ok= 1

    # set to 0 if the above fails, and, we are using dhcp in which
    # case we don't know the ip of this machine (without having to
    # parse ifconfig or something). In that case, we won't be able
    # to make api calls, so printing a message to the screen will
    # have to suffice.
    can_make_api_call= 1

    log.write( "Checking that hostname %s resolves\n" % hostname )

    # try a regular dns lookup first
    try:
        resolved_node_ip= socket.gethostbyname(hostname)
    except socket.gaierror, e:
        hostname_resolve_ok= 0
        

    if INTERFACE_SETTINGS['method'] == "dhcp":
        if hostname_resolve_ok:
            INTERFACE_SETTINGS['ip']= resolved_node_ip
            node_ip= resolved_node_ip
        else:
            can_make_api_call= 0
    else:
        node_ip= INTERFACE_SETTINGS['ip']

    # make sure the dns lookup matches what the configuration file says
    if hostname_resolve_ok:
        if node_ip != resolved_node_ip:
            log.write( "Hostname %s does not resolve to %s, but %s:\n" % \
                       (hostname,node_ip,resolved_node_ip) )
            hostname_resolve_ok= 0
        else:
            log.write( "Hostname %s correctly resolves to %s:\n" %
                       (hostname,node_ip) )

        
    vars["INTERFACE_SETTINGS"]= INTERFACE_SETTINGS

    if (not hostname_resolve_ok and not vars['DISCONNECTED_OPERATION'] and
        'NAT_MODE' not in vars):
        log.write( "Hostname does not resolve correctly, will not continue.\n" )

        if can_make_api_call:
            log.write( "Notifying contacts of problem.\n" )

            vars['RUN_LEVEL']= 'failboot'
            vars['STATE_CHANGE_NOTIFY']= 1
            vars['STATE_CHANGE_NOTIFY_MESSAGE']= \
                                     notify_messages.MSG_HOSTNAME_NOT_RESOLVE
            
            UpdateRunLevelWithPLC.Run( vars, log )
                    
        log.write( "\n\n" )
        log.write( "The hostname and/or ip in the network configuration\n" )
        log.write( "file do not resolve and match.\n" )
        log.write( "Please make sure the hostname set in the network\n" )
        log.write( "configuration file resolves to the ip also specified\n" )
        log.write( "there.\n\n" )
        log.write( "Debug mode is being started on this cd. When the above\n" )
        log.write( "is corrected, reboot the machine to try again.\n" )
        
        raise BootManagerException, \
              "Configured node hostname does not resolve."
    
    return 1
