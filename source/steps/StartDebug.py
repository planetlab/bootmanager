#!/usr/bin/python2

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import os

from Exceptions import *
import utils
import compatibility


message= \
"""
---------------------------------------------------------
This machine has entered a temporary debug state, so
Planetlab Support can login and fix any problems that
might have occurred.

Please do not reboot this machine at this point, unless
specifically asked to.

Thank you.
---------------------------------------------------------
"""


def Run( vars, log ):
    """
    Bring up sshd inside the boot cd environment for debug purposes.

    Once its running, touch the file /tmp/SSHD_RUNNING so future
    calls to this function don't do anything.

    Expect the following variables in vars to be set:
    BM_SOURCE_DIR     The source dir for the boot manager sources that
                      we are currently running from
    BOOT_CD_VERSION          A tuple of the current bootcd version
    """

    log.write( "\n\nStep: Starting debug mode.\n" )
    
    # make sure we have the variables we need
    try:
        BM_SOURCE_DIR= vars["BM_SOURCE_DIR"]
        if BM_SOURCE_DIR == "":
            raise ValueError, "BM_SOURCE_DIR"

        BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        if BOOT_CD_VERSION == "":
            raise ValueError, "BOOT_CD_VERSION"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    log.write( "Starting debug environment\n" )

    ssh_source_files= "%s/debug_files/" % BM_SOURCE_DIR    
    ssh_dir= "/etc/ssh/"
    ssh_home= "/root/.ssh"
    cancel_boot_flag= "/tmp/CANCEL_BOOT"
    sshd_started_flag= "/tmp/SSHD_RUNNING"
    
    sshd_started= 0
    try:
        os.stat(sshd_started_flag)
        sshd_started= 1
    except OSError, e:
        pass

    if not sshd_started:
        # NOTE: these commands hang if ssh_host_*_key files exist, b/c 
        #     ssh-keygen asks for user input to confirm the overwrite.  
		#     could fix this with "echo 'y' | "
        log.write( "Creating ssh host keys\n" )
        
        utils.makedirs( ssh_dir )
        utils.sysexec( "ssh-keygen -t rsa1 -b 1024 -f %s/ssh_host_key -N ''" %
                       ssh_dir, log )
        utils.sysexec( "ssh-keygen -t rsa -f %s/ssh_host_rsa_key -N ''" %
                       ssh_dir, log )
        utils.sysexec( "ssh-keygen -d -f %s/ssh_host_dsa_key -N ''" %
                       ssh_dir, log )

        if BOOT_CD_VERSION[0] >= 3:
            utils.sysexec( "cp -f %s/sshd_config_v3 %s/sshd_config" %
                           (ssh_source_files,ssh_dir), log )
        else:
            utils.sysexec( "cp -f %s/sshd_config_v2 %s/sshd_config" %
                           (ssh_source_files,ssh_dir), log )
    else:
        log.write( "ssh host keys already created\n" )


    # always update the key, may have change in this instance of the bootmanager
    log.write( "Installing debug ssh key for root user\n" )
    
    utils.makedirs( ssh_home )
    utils.sysexec( "cp -f %s/debug_root_ssh_key %s/authorized_keys" %
                   (ssh_source_files,ssh_home), log )
    utils.sysexec( "chmod 700 %s" % ssh_home, log )
    utils.sysexec( "chmod 600 %s/authorized_keys" % ssh_home, log )

    if not sshd_started:
        log.write( "Starting sshd\n" )
        
        if BOOT_CD_VERSION[0] == 2:
            utils.sysexec( "/usr/sbin/sshd", log )
        else:
            utils.sysexec( "service sshd start", log )
        
        # flag that ssh is running
        utils.sysexec( "touch %s" % sshd_started_flag, log )
    else:
        log.write( "sshd already running\n" )

    
    # this will make the initial script stop requesting scripts from PLC
    utils.sysexec( "touch %s" % cancel_boot_flag, log )

    # for ease of use, setup lvm on 2.x cds
    if BOOT_CD_VERSION[0] == 2:
        compatibility.setup_lvm_2x_cd(vars,log)

    print message
    
    return

