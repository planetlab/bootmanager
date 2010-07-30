#!/usr/bin/python
#
# $Id$
# $URL$
#
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
    exist in /boot
    
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

        for filesystem in ("root","vservers"):
            try:
                # first run fsck to prevent fs corruption from hanging mount...
                log.write( "fsck %s file system\n" % filesystem )
                utils.sysexec("e2fsck -v -p %s" % (PARTITIONS[filesystem]),log)
            except BootManagerException, e:
                log.write( "BootManagerException during fsck of %s (%s) filesystem : %s\n" %
                           (filesystem, PARTITIONS[filesystem], str(e)) )
                try:
                    log.write( "Trying to recover filesystem errors on %s\n" % filesystem )
                    utils.sysexec("e2fsck -v -y %s" % (PARTITIONS[filesystem]),log)
                except BootManagerException, e:
                    log.write( "BootManagerException during trying to recover filesystem errors on %s (%s) filesystem : %s\n" %
                           (filesystem, PARTITIONS[filesystem], str(e)) )
                    return -1
            else:
                # disable time/count based filesystems checks
                utils.sysexec_noerr( "tune2fs -c -1 -i 0 %s" % PARTITIONS[filesystem], log)

        try:
            # then attempt to mount them
            log.write( "mounting root file system\n" )
            utils.sysexec("mount -t ext3 %s %s" % (PARTITIONS["root"],SYSIMG_PATH),log)
        except BootManagerException, e:
            log.write( "BootManagerException during mount of /root: %s\n" % str(e) )
            return -2
            
        try:
            PROC_PATH = "%s/proc" % SYSIMG_PATH
            utils.makedirs(PROC_PATH)
            log.write( "mounting /proc\n" )
            utils.sysexec( "mount -t proc none %s" % PROC_PATH, log )
        except BootManagerException, e:
            log.write( "BootManagerException during mount of /proc: %s\n" % str(e) )
            return -2

        try:
            VSERVERS_PATH = "%s/vservers" % SYSIMG_PATH
            utils.makedirs(VSERVERS_PATH)
            log.write( "mounting vserver partition in root file system\n" )
            utils.sysexec("mount -t ext3 %s %s" % (PARTITIONS["vservers"], VSERVERS_PATH), log)
        except BootManagerException, e:
            log.write( "BootManagerException during mount of /vservers: %s\n" % str(e) )
            return -2

        ROOT_MOUNTED= 1
        vars['ROOT_MOUNTED']= 1
        
    # check if the base kernel is installed 
    # these 2 links are created by our kernel's post-install scriplet
    log.write("Checking for a custom kernel\n")
    try:
        os.stat("%s/boot/kernel-boot" % SYSIMG_PATH)
    except OSError, e:            
        log.write( "Couldn't locate base kernel (you might be using the stock kernel).\n")
        return -3

    # check if the model specified kernel is installed
    option = ''
    if NODE_MODEL_OPTIONS & ModelOptions.SMP:
        option = 'smp'
        try:
            os.stat("%s/boot/kernel-boot%s" % (SYSIMG_PATH,option))
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

    log.write( "Node installation appears to be ok\n" )
    
    return 1
