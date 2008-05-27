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
    BOOT_CD_VERSION                     A tuple of the current bootcd version
    SKIP_HARDWARE_REQUIREMENT_CHECK     Whether or not we should skip hardware
                                        requirement checks
                                        
    The following keys are set/updated:
    WAS_NODE_ID_IN_CONF                 Set to 1 if the node id was in the conf file
    WAS_NODE_KEY_IN_CONF                Set to 1 if the node key was in the conf file
    BOOT_STATE                          The current node boot state
    NODE_MODEL                          The user specified model of this node
    NODE_MODEL_OPTIONS                  The options extracted from the user specified
                                                model of this node 
    SKIP_HARDWARE_REQUIREMENT_CHECK     Whether or not we should skip hardware
                                                requirement checks
    NODE_SESSION                        The session value returned from BootGetNodeDetails
    INTERFACES                          The network interfaces associated with this node
    INTERFACE_SETTINGS                  A dictionary of the values of the interface settings
    
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

        INTERFACE_SETTINGS= vars["INTERFACE_SETTINGS"]
        if INTERFACE_SETTINGS == "":
            raise ValueError, "INTERFACE_SETTINGS"

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

    node_details= BootAPI.call_api_function( vars, "GetNodes", 
                                             (vars['NODE_ID'], 
                                              ['boot_state', 'nodegroup_ids', 'interface_ids', 'model', 'site_id']))[0]

    vars['BOOT_STATE']= node_details['boot_state']
    vars['NODE_MODEL']= string.strip(node_details['model'])
    vars['SITE_ID'] = node_details['site_id'] 
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
    interfaces= BootAPI.call_api_function( vars, "GetInterfaces", (node_details['interface_ids'],))
    got_primary= 0
    for network in interfaces:
        if network['is_primary'] == 1:
            log.write( "Primary network as returned from PLC: %s\n" % str(network) )
            got_primary= 1
            break

    if not got_primary:
        raise BootManagerException, "Node did not have a primary network."

    vars['INTERFACES']= interfaces
    
    return 1
