#!/usr/bin/python2

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.
# expected /proc/partitions format

from Exceptions import *
import utils
import os


def Run( vars, log ):
    """
    Initialize the node:
    - runs planetlabconf

    Except the following variables from the store:
    SYSIMG_PATH             the path where the system image will be mounted
    (always starts with TEMP_PATH)
    NODE_ID                  The db node_id for this machine
    PLCONF_DIR               The directory to store the configuration file in
    
    Sets the following variables:
    None
    
    """

    log.write( "\n\nStep: Install: Final node initialization.\n" )

    # make sure we have the variables we need
    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"
        
        NODE_ID= vars["NODE_ID"]
        if NODE_ID == "":
            raise ValueError, "NODE_ID"

        PLCONF_DIR= vars["PLCONF_DIR"]
        if PLCONF_DIR == "":
            raise ValueError, "PLCONF_DIR"
        
    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    log.write( "Running PlanetLabConf to update any configuration files\n" )

    # PlanetLabConf requires /etc/planetlab/node_id, which is normally
    # maintained in ValidateNodeInstal. so, write out the node_id here
    # so PlanetLabConf can run.
    try:
        node_id_file_path= "%s/%s/node_id" % (SYSIMG_PATH,PLCONF_DIR)
        node_id_file= file( node_id_file_path, "w" )
        node_id_file.write( str(NODE_ID) )
        node_id_file.close()
        node_id_file= None
    except IOError, e:
        raise BootManagerException, \
                  "Unable to write out /etc/planetlab/node_id for PlanetLabConf"

    if not utils.sysexec( "chroot %s PlanetLabConf.py noscripts" %
                          SYSIMG_PATH, log ):
        log.write( "PlanetLabConf failed, install incomplete.\n" )
        return 0
                
    services= [ "netfs", "rawdevices", "cpuspeed", "smartd" ]
    for service in services:
        if os.path.exists("%s/etc/init.d/%s" % (SYSIMG_PATH,service)):
            log.write( "Disabling unneeded service: %s\n" % service )
            utils.sysexec( "chroot %s chkconfig --level 12345 %s off" %
                           (SYSIMG_PATH,service), log )
            
    return 1
