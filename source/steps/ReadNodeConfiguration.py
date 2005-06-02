# Copyright (c) 2003 Intel Corporation
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.

#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.

#     * Neither the name of the Intel Corporation nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE INTEL OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# EXPORT LAWS: THIS LICENSE ADDS NO RESTRICTIONS TO THE EXPORT LAWS OF
# YOUR JURISDICTION. It is licensee's responsibility to comply with any
# export regulations applicable in licensee's jurisdiction. Under
# CURRENT (May 2000) U.S. export regulations this software is eligible
# for export from the U.S. and can be downloaded by or otherwise
# exported or reexported worldwide EXCEPT to U.S. embargoed destinations
# which include Cuba, Iraq, Libya, North Korea, Iran, Syria, Sudan,
# Afghanistan and any other country to which the U.S. has embargoed
# goods and services.


import sys, os, traceback
import string
import socket

import utils
from Exceptions import *
import BootServerRequest
import BootAPI
import StartDebug
import notify_messages
import UpdateBootStateWithPLC


# two possible names of the configuration files
NEW_CONF_FILE_NAME= "plnode.txt"
OLD_CONF_FILE_NAME= "planet.cnf"


def Run( vars, log ):   
    """
    read the machines node configuration file, which contains
    the node key and the node_id for this machine.
    
    these files can exist in several different locations with
    several different names. Below is the search order:

    filename      floppy   flash    cd
    plnode.txt      1        2      4 (/usr/boot), 5 (/usr)
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
    BOOT_CD_VERSION          A tuple of the current bootcd version
    SUPPORT_FILE_DIR         directory on the boot servers containing
                             scripts and support files
    
    Sets the following variables from the configuration file:
    WAS_NODE_ID_IN_CONF         Set to 1 if the node id was in the conf file
    WAS_NODE_KEY_IN_CONF         Set to 1 if the node key was in the conf file
    NONE_ID                     The db node_id for this machine
    NODE_KEY                    The key for this node
    NETWORK_SETTINGS            A dictionary of the values from the network
                                configuration file. keys set:
                                   method
                                   ip        
                                   mac       
                                   gateway   
                                   network   
                                   broadcast 
                                   netmask   
                                   dns1      
                                   dns2      
                                   hostname  
                                   domainname
    """

    log.write( "\n\nStep: Reading node configuration file.\n" )


    # make sure we have the variables we need
    try:
        BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        if BOOT_CD_VERSION == "":
            raise ValueError, "BOOT_CD_VERSION"

        SUPPORT_FILE_DIR= vars["SUPPORT_FILE_DIR"]
        if SUPPORT_FILE_DIR == None:
            raise ValueError, "SUPPORT_FILE_DIR"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    NETWORK_SETTINGS= {}
    NETWORK_SETTINGS['method']= "dhcp"
    NETWORK_SETTINGS['ip']= ""
    NETWORK_SETTINGS['mac']= ""
    NETWORK_SETTINGS['gateway']= ""
    NETWORK_SETTINGS['network']= ""
    NETWORK_SETTINGS['broadcast']= ""
    NETWORK_SETTINGS['netmask']= ""
    NETWORK_SETTINGS['dns1']= ""
    NETWORK_SETTINGS['dns2']= ""
    NETWORK_SETTINGS['hostname']= "localhost"
    NETWORK_SETTINGS['domainname']= "localdomain"
    vars['NETWORK_SETTINGS']= NETWORK_SETTINGS

    vars['NODE_ID']= 0
    vars['NODE_KEY']= ""

    vars['WAS_NODE_ID_IN_CONF']= 0
    vars['WAS_NODE_KEY_IN_CONF']= 0

    # for any devices that need to be mounted to get the configuration
    # file, mount them here.
    mount_point= "/tmp/conffilemount"
    utils.makedirs( mount_point )

    old_conf_file_contents= None
    conf_file_contents= None
    
    
    # 1. check the regular floppy device
    log.write( "Checking standard floppy disk for plnode.txt file.\n" )
    
    utils.sysexec_noerr( "mount -o ro -t ext2,msdos /dev/fd0 %s " \
                         % mount_point, log )

    conf_file_path= "%s/%s" % (mount_point,NEW_CONF_FILE_NAME)
    if os.access( conf_file_path, os.R_OK ):
        try:
            conf_file= file(conf_file_path,"r")
            conf_file_contents= conf_file.read()
            conf_file.close()
        except IOError, e:
            pass

        utils.sysexec_noerr( "umount /dev/fd0", log )
        if __parse_configuration_file( vars, log, conf_file_contents):
            return 1
        else:
            raise BootManagerException( "Found configuration file plnode.txt " \
                                        "on floppy, but was unable to parse it." )


    # try the old file name, same device. its actually number 3 on the search
    # order, but do it now to save mounting/unmounting the disk twice.
    # try to parse it later...
    conf_file_path= "%s/%s" % (mount_point,OLD_CONF_FILE_NAME)
    if os.access( conf_file_path, os.R_OK ):
        try:
            old_conf_file= file(conf_file_path,"r")
            old_conf_file_contents= old_conf_file.read()
            old_conf_file.close()
        except IOError, e:
            pass
        
    utils.sysexec_noerr( "umount /dev/fd0", log )



    if BOOT_CD_VERSION[0] == 3:
        # 2. check flash devices on 3.0 based cds
        log.write( "Checking flash devices for plnode.txt file.\n" )

        # this is done the same way the 3.0 cds do it, by attempting
        # to mount and sd*1 devices that are removable
        devices= os.listdir("/sys/block/")

        for device in devices:
            if device[:2] != "sd":
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
                continue

            log.write( "Checking removable device %s\n" % device )
        
            # ok, try to mount it and see if we have a conf file.
            full_device= "/dev/%s1" % device

            try:
                utils.sysexec( "mount -o ro -t ext2,msdos %s %s" \
                               % (full_device,mount_point), log )
            except BootManagerException, e:
                continue
            
            conf_file_path= "%s/%s" % (mount_point,NEW_CONF_FILE_NAME)
            if os.access( conf_file_path, os.R_OK ):
                try:
                    conf_file= file(conf_file_path,"r")
                    conf_file_contents= conf_file.read()
                    conf_file.close()
                except IOError, e:
                    pass

            utils.sysexec_noerr( "umount %s" % full_device, log )
            if __parse_configuration_file( vars, log, conf_file_contents):
                return 1
            else:
                raise BootManagerException("Found configuration file plnode.txt " \
                                           "on floppy, but was unable to parse it.")
            

            
    # 3. check standard floppy disk for old file name planet.cnf
    log.write( "Checking standard floppy disk for planet.cnf file.\n" )

    if old_conf_file_contents:
        if __parse_configuration_file( vars, log, old_conf_file_contents):
            return 1
        else:
            raise BootManagerException( "Found configuration file planet.cnf " \
                                        "on floppy, but was unable to parse it." )


    # 4. check for plnode.txt in /usr/boot (mounted already)
    log.write( "Checking /usr/boot (cd) for plnode.txt file.\n" )
    
    conf_file_path= "/usr/boot/%s" % NEW_CONF_FILE_NAME
    if os.access(conf_file_path,os.R_OK):
        try:
            conf_file= file(conf_file_path,"r")
            conf_file_contents= conf_file.read()
            conf_file.close()
        except IOError, e:
            pass    
    
        if __parse_configuration_file( vars, log, conf_file_contents):            
            return 1
        else:
            raise BootManagerException( "Found configuration file plnode.txt " \
                                        "in /usr/boot, but was unable to parse it.")



    # 5. check for plnode.txt in /usr (mounted already)
    log.write( "Checking /usr (cd) for plnode.txt file.\n" )
    
    conf_file_path= "/usr/%s" % NEW_CONF_FILE_NAME
    if os.access(conf_file_path,os.R_OK):
        try:
            conf_file= file(conf_file_path,"r")
            conf_file_contents= conf_file.read()
            conf_file.close()
        except IOError, e:
            pass    
    
        if __parse_configuration_file( vars, log, conf_file_contents):            
            return 1
        else:
            raise BootManagerException( "Found configuration file plnode.txt " \
                                        "in /usr, but was unable to parse it.")


    raise BootManagerException, "Unable to find and read a node configuration file."
    



def __parse_configuration_file( vars, log, file_contents ):
    """
    parse a configuration file, set keys in var NETWORK_SETTINGS
    in vars (see comment for function ReadNodeConfiguration)
    """

    BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
    SUPPORT_FILE_DIR= vars["SUPPORT_FILE_DIR"]
    NETWORK_SETTINGS= vars["NETWORK_SETTINGS"]
    
    if file_contents is None:
        return 0
    
    try:
        line_num= 0
        for line in file_contents.split("\n"):

            line_num = line_num + 1
            
            # if its a comment or a whitespace line, ignore
            if line[:1] == "#" or string.strip(line) == "":
                continue

            # file is setup as name="value" pairs
            parts= string.split(line,"=")
            if len(parts) != 2:
                log.write( "Invalid line %d in configuration file:\n" % line_num )
                log.write( line + "\n" )
                return 0

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
                NETWORK_SETTINGS['method']= value.strip()

            if name == "IP_ADDRESS":
                NETWORK_SETTINGS['ip']= value.strip()

            if name == "IP_GATEWAY":
                NETWORK_SETTINGS['gateway']= value.strip()

            if name == "IP_NETMASK":
                NETWORK_SETTINGS['netmask']= value.strip()

            if name == "IP_NETADDR":
                NETWORK_SETTINGS['network']= value.strip()

            if name == "IP_BROADCASTADDR":
                NETWORK_SETTINGS['broadcast']= value.strip()

            if name == "IP_DNS1":
                NETWORK_SETTINGS['dns1']= value.strip()

            if name == "IP_DNS2":
                NETWORK_SETTINGS['dns2']= value.strip()

            if name == "HOST_NAME":
                NETWORK_SETTINGS['hostname']= string.lower(value)

            if name == "DOMAIN_NAME":
                NETWORK_SETTINGS['domainname']= string.lower(value)

    except IndexError, e:
        log.write( "Unable to parse configuration file\n" )
        return 0

    # now if we are set to dhcp, clear out any fields
    # that don't make sense
    if NETWORK_SETTINGS["method"] == "dhcp":
        NETWORK_SETTINGS["ip"]= ""
        NETWORK_SETTINGS["gateway"]= ""     
        NETWORK_SETTINGS["netmask"]= ""
        NETWORK_SETTINGS["network"]= ""
        NETWORK_SETTINGS["broadcast"]= ""
        NETWORK_SETTINGS["dns1"]= ""
        NETWORK_SETTINGS["dns2"]= ""


    log.write("Successfully read and parsed node configuration file.\n" )

    
    if vars['NODE_ID'] is None or vars['NODE_ID'] == 0:
        log.write( "Configuration file does not contain the node_id value.\n" )
        log.write( "Querying PLC for node_id.\n" )

        bs_request= BootServerRequest.BootServerRequest()

        try:
            ifconfig_file= file("/tmp/ifconfig","r")
            ifconfig= ifconfig_file.read()
            ifconfig_file.close()
        except IOError:
            log.write( "Unable to read ifconfig output from /tmp/ifconfig\n" )
            return 0
        
        postVars= {"ifconfig" : ifconfig}
        result= bs_request.DownloadFile( "%s/getnodeid.php" %
                                         SUPPORT_FILE_DIR,
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
        if BOOT_CD_VERSION[0] == 2:
            read_mode= "rb"
        else:
            read_mode= "r"
            
        try:
            nonce_file= file("/tmp/nonce",read_mode)
            nonce= nonce_file.read()
            nonce_file.close()
        except IOError:
            log.write( "Unable to read nonce from /tmp/nonce\n" )
            return 0

        if BOOT_CD_VERSION[0] == 2:
            nonce= nonce.encode('hex')

            # there is this nice bug in the php that currently accepts the
            # nonce for the old scripts, in that if the nonce contains
            # null chars (2.x cds sent as binary), then
            # the nonce is truncated. so, do the same here, truncate the nonce
            # at the first null ('00'). This could leave us with an empty string.
            nonce_len= len(nonce)
            for byte_index in range(0,nonce_len,2):
                if nonce[byte_index:byte_index+2] == '00':
                    nonce= nonce[:byte_index]
                    break
        else:
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

    hostname= NETWORK_SETTINGS['hostname'] + "." + \
              NETWORK_SETTINGS['domainname']

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
        

    if NETWORK_SETTINGS['method'] == "dhcp":
        if hostname_resolve_ok:
            NETWORK_SETTINGS['ip']= resolved_node_ip
            node_ip= resolved_node_ip
        else:
            can_make_api_call= 0
    else:
        node_ip= NETWORK_SETTINGS['ip']

    # make sure the dns lookup matches what the configuration file says
    if hostname_resolve_ok:
        if node_ip != resolved_node_ip:
            log.write( "Hostname %s does not resolve to %s, but %s:\n" % \
                       (hostname,node_ip,resolved_node_ip) )
            hostname_resolve_ok= 0
        else:
            log.write( "Hostname %s correctly resolves to %s:\n" %
                       (hostname,node_ip) )


    # 3.x cds, with a node_key on the floppy, can update their mac address
    # at plc, so get it here
    if BOOT_CD_VERSION[0] == 3 and vars['WAS_NODE_ID_IN_CONF'] == 1:
        eth_device= "eth0"
        try:
            hw_addr_file= file("/sys/class/net/%s/address" % eth_device, "r")
            hw_addr= hw_addr_file.read().strip().upper()
            hw_addr_file.close()
        except IOError, e:
            raise BootmanagerException, \
                  "could not get hw address for device %s" % eth_device

        NETWORK_SETTINGS['mac']= hw_addr

        
    vars["NETWORK_SETTINGS"]= NETWORK_SETTINGS

    if not hostname_resolve_ok:
        log.write( "Hostname does not resolve correctly, will not continue.\n" )

        StartDebug.Run( vars, log )

        if can_make_api_call:
            log.write( "Notifying contacts of problem.\n" )

            vars['BOOT_STATE']= 'dbg'
            vars['STATE_CHANGE_NOTIFY']= 1
            vars['STATE_CHANGE_NOTIFY_MESSAGE']= \
                                     notify_messages.MSG_HOSTNAME_NOT_RESOLVE
            
            UpdateBootStateWithPLC.Run( vars, log )
                    
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
