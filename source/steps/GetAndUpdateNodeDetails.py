#!/usr/bin/python2

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import string

from Exceptions import *
import BootAPI
import ModelOptions

def Run( vars, log ):
    """

    Contact PLC and get the attributes for this node. Also, parse in
    options from the node model strong.

    Also, update any node network settings at PLC, minus the ip address,
    so, upload the mac (if node_id was in conf file), gateway, network,
    broadcast, netmask, dns1/2, and the hostname/domainname.

    Expect the following keys to be set:
    BOOT_CD_VERSION          A tuple of the current bootcd version
    SKIP_HARDWARE_REQUIREMENT_CHECK     Whether or not we should skip hardware
                                        requirement checks
                                        
    The following keys are set/updated:
    WAS_NODE_ID_IN_CONF      Set to 1 if the node id was in the conf file
    WAS_NODE_KEY_IN_CONF     Set to 1 if the node key was in the conf file
    BOOT_STATE               The current node boot state
    NODE_MODEL               The user specified model of this node
    NODE_MODEL_OPTIONS       The options extracted from the user specified
                             model of this node 
    NETWORK_SETTINGS         A dictionary of the values of the network settings
    SKIP_HARDWARE_REQUIREMENT_CHECK     Whether or not we should skip hardware
                                        requirement checks
    NODE_SESSION             The session value returned from BootGetNodeDetails
    
    Return 1 if able to contact PLC and get node info.
    Raise a BootManagerException if anything fails.
    """

    log.write( "\n\nStep: Retrieving details of node from PLC.\n" )

    # make sure we have the variables we need
    try:
        BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        if BOOT_CD_VERSION == "":
            raise ValueError, "BOOT_CD_VERSION"

        SKIP_HARDWARE_REQUIREMENT_CHECK= vars["SKIP_HARDWARE_REQUIREMENT_CHECK"]
        if SKIP_HARDWARE_REQUIREMENT_CHECK == "":
            raise ValueError, "SKIP_HARDWARE_REQUIREMENT_CHECK"

        NETWORK_SETTINGS= vars["NETWORK_SETTINGS"]
        if NETWORK_SETTINGS == "":
            raise ValueError, "NETWORK_SETTINGS"

        WAS_NODE_ID_IN_CONF= vars["WAS_NODE_ID_IN_CONF"]
        if WAS_NODE_ID_IN_CONF == "":
            raise ValueError, "WAS_NODE_ID_IN_CONF"

        WAS_NODE_KEY_IN_CONF= vars["WAS_NODE_KEY_IN_CONF"]
        if WAS_NODE_KEY_IN_CONF == "":
            raise ValueError, "WAS_NODE_KEY_IN_CONF"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    details= BootAPI.call_api_function( vars, "BootGetNodeDetails", () )

    vars['BOOT_STATE']= details['boot_state']
    vars['NODE_MODEL']= string.strip(details['model'])
    vars['NODE_SESSION']= details['session']
    
    log.write( "Successfully retrieved node record.\n" )
    log.write( "Current boot state: %s\n" % vars['BOOT_STATE'] )
    log.write( "Node make/model: %s\n" % vars['NODE_MODEL'] )
    
    # parse in the model options from the node_model string
    model= vars['NODE_MODEL']
    options= ModelOptions.Get(model)
    vars['NODE_MODEL_OPTIONS']=options

    # Check if we should skip hardware requirement check
    if options & ModelOptions.MINHW:
        vars['SKIP_HARDWARE_REQUIREMENT_CHECK']=1
        log.write( "node model indicates override to hardware requirements.\n" )

    # this contains all the node networks, for now, we are only concerned
    # in the primary network
    node_networks= details['networks']
    got_primary= 0
    for network in node_networks:
        if network['is_primary'] == 1:
            got_primary= 1
            break

    if not got_primary:
        raise BootManagerException, "Node did not have a primary network."
    
    log.write( "Primary network as returned from PLC: %s\n" % str(network) )

    # if we got this far, the ip on the floppy and the ip in plc match,
    # make the rest of the PLC information match whats on the floppy
    network['method']= NETWORK_SETTINGS['method']

    # only nodes that have the node_id specified directly in the configuration
    # file can change their mac address
    if WAS_NODE_ID_IN_CONF == 1:
        network['mac']= NETWORK_SETTINGS['mac']
        
    network['gateway']= NETWORK_SETTINGS['gateway']
    network['network']= NETWORK_SETTINGS['network']
    network['broadcast']= NETWORK_SETTINGS['broadcast']
    network['netmask']= NETWORK_SETTINGS['netmask']
    network['dns1']= NETWORK_SETTINGS['dns1']
    network['dns2']= NETWORK_SETTINGS['dns2']
    
    log.write( "Updating network settings at PLC to match floppy " \
               "(except for node ip).\n" )
    update_vals= {}
    update_vals['primary_network']= network
    BootAPI.call_api_function( vars, "BootUpdateNode", (update_vals,) )
    
    return 1
