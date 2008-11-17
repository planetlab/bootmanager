#!/usr/bin/python

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import os

from Exceptions import *
import utils
import systeminfo
import ModelOptions


def Run( vars, log ):
    """
    See if a node installation is valid. More checks should certainly be
    done in the future, but for now, make sure that the sym links kernel-boot
    and initrd-boot exist in /boot
    
    Expect the following variables to be set:
    SYSIMG_PATH              the path where the system image will be mounted
                             (always starts with TEMP_PATH)
    ROOT_MOUNTED             the node root file system is mounted
    NODE_ID                  The db node_id for this machine
    PLCONF_DIR               The directory to store the configuration file in
    
    Set the following variables upon successfully running:
    ROOT_MOUNTED             the node root file system is mounted
    """

    log.write( "\n\nStep: Validating node installation.\n" )

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
        
        NODE_MODEL_OPTIONS= vars["NODE_MODEL_OPTIONS"]

        PARTITIONS= vars["PARTITIONS"]
        if PARTITIONS == None:
            raise ValueError, "PARTITIONS"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    ROOT_MOUNTED= 0
    if vars.has_key('ROOT_MOUNTED'):
        ROOT_MOUNTED= vars['ROOT_MOUNTED']

    # mount the root system image if we haven't already.
    # capture BootManagerExceptions during the vgscan/change and mount
    # calls, so we can return 0 instead
    if ROOT_MOUNTED == 0:
            
        # simply creating an instance of this class and listing the system
        # block devices will make them show up so vgscan can find the planetlab
        # volume group
        systeminfo.get_block_device_list(vars, log)

        try:
            utils.sysexec( "vgscan", log )
            utils.sysexec( "vgchange -ay planetlab", log )
        except BootManagerException, e:
            log.write( "BootManagerException during vgscan/vgchange: %s\n" %
                       str(e) )
            return 0
            
        utils.makedirs( SYSIMG_PATH )

        try:
            log.write( "mounting root file system\n" )
            utils.sysexec("mount -t ext3 %s %s" % (PARTITIONS["root"],SYSIMG_PATH),log)

            log.write( "mounting vserver partition in root file system\n" )
            utils.sysexec("mount -t ext3 %s %s/vservers" % \
                          (PARTITIONS["vservers"], SYSIMG_PATH), log)

            log.write( "mounting /proc\n" )
            utils.sysexec( "mount -t proc none %s/proc" % SYSIMG_PATH, log )
        except BootManagerException, e:
            log.write( "BootManagerException during mount of /root, /vservers and /proc: %s\n" %
                       str(e) )
            return 0

        ROOT_MOUNTED= 1
        vars['ROOT_MOUNTED']= 1
        
    
    # check if the base kernel is installed
    try:
        os.stat("%s/boot/kernel-boot" % SYSIMG_PATH)
        os.stat("%s/boot/initrd-boot" % SYSIMG_PATH)
    except OSError, e:            
        log.write( "FATAL: Couldn't locate base kernel.\n")                
        return 0

    # check if the model specified kernel is installed
    option = ''
    if NODE_MODEL_OPTIONS & ModelOptions.SMP:
        option = 'smp'
        try:
            os.stat("%s/boot/kernel-boot%s" % (SYSIMG_PATH,option))
            os.stat("%s/boot/initrd-boot%s" % (SYSIMG_PATH,option))
        except OSError, e:
            # smp kernel is not there; remove option from modeloptions
            # such that the rest of the code base thinks we are just
            # using the base kernel.
            NODE_MODEL_OPTIONS = NODE_MODEL_OPTIONS & ~ModelOptions.SMP
            vars["NODE_MODEL_OPTIONS"] = NODE_MODEL_OPTIONS
            log.write( "WARNING: Couldn't locate smp kernel.\n")
            
    # write out the node id to /etc/planetlab/node_id. if this fails, return
    # 0, indicating the node isn't a valid install.
    try:
        node_id_file_path= "%s/%s/node_id" % (SYSIMG_PATH,PLCONF_DIR)
        node_id_file= file( node_id_file_path, "w" )
        node_id_file.write( str(NODE_ID) )
        node_id_file.close()
        node_id_file= None
        log.write( "Updated /etc/planetlab/node_id\n" )
    except IOError, e:
        log.write( "Unable to write out /etc/planetlab/node_id\n" )
        return 0

    log.write( "Everything appears to be ok\n" )
    
    return 1
