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


warning_message= \
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

# this can be invoked 
# either at the end of the bm logic, because something failed (last_resort = True)
# and/or it can be invoked as a fallback very early in the bootmanager logic,
# so we can reach the node regardless of what happens (e.g. bm sometimes hangs)

def Run( vars, log, last_resort = True):

    """
    Bring up sshd inside the boot cd environment for debug purposes.

    Once its running, touch the file /tmp/SSHD_RUNNING so future
    calls to this function don't do anything.

    Expect the following variables in vars to be set:
    BM_SOURCE_DIR     The source dir for the boot manager sources that
                      we are currently running from
    BOOT_CD_VERSION          A tuple of the current bootcd version
    """

    if last_resort:
        message="Starting debug mode"
    else:
        message="Starting fallback sshd"


    log.write( "\n\nStep: %s.\n"%message )
    
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

    # constants
    ssh_source_files= "%s/debug_files/" % BM_SOURCE_DIR    
    ssh_dir= "/etc/ssh/"
    ssh_home= "/root/.ssh"
    cancel_boot_flag= "/tmp/CANCEL_BOOT"
    sshd_started_flag= "/tmp/SSHD_RUNNING"
    
    # create host keys if needed
    if not os.path.isdir (ssh_dir):
        utils.makedirs (ssh_dir)
    key=ssh_dir+"/ssh_host_key"
    if not os.path.isfile (key):
        log.write("Creating host rsa1 key %s\n"%key)
        utils.sysexec( "ssh-keygen -t rsa1 -b 1024 -f %s -N ''" % key, log )
    key=ssh_dir+"/ssh_host_rsa_key"
    if not os.path.isfile (key):
        log.write("Creating host rsa key %s\n"%key)
        utils.sysexec( "ssh-keygen -t rsa -f %s -N ''" % key, log )
    key=ssh_dir+"/ssh_host_dsa_key"
    if not os.path.isfile (key):
        log.write("Creating host dsa key %s\n"%key)
        utils.sysexec( "ssh-keygen -d -f %s -N ''" % key, log )

    if BOOT_CD_VERSION[0] >= 3:
        utils.sysexec( "cp -f %s/sshd_config_v3 %s/sshd_config" % (ssh_source_files,ssh_dir), log )
    else:
        utils.sysexec( "cp -f %s/sshd_config_v2 %s/sshd_config" % (ssh_source_files,ssh_dir), log )

    # always update the key, may have changed in this instance of the bootmanager
    log.write( "Installing debug ssh key for root user\n" )
    if not os.path.isdir ( ssh_home):
        utils.makedirs( ssh_home )
    utils.sysexec( "cp -f %s/debug_root_ssh_key %s/authorized_keys" % (ssh_source_files,ssh_home), log )
    utils.sysexec( "chmod 700 %s" % ssh_home, log )
    utils.sysexec( "chmod 600 %s/authorized_keys" % ssh_home, log )

    # start sshd
    if not os.path.isfile(sshd_started_flag):
        log.write( "Starting sshd\n" )
        if BOOT_CD_VERSION[0] == 2: utils.sysexec( "/usr/sbin/sshd", log )
        else:                       utils.sysexec( "service sshd start", log )
        # flag that ssh is running
        utils.sysexec( "touch %s" % sshd_started_flag, log )
    else:
        # it is expected that sshd is already running when last_resort==True
        if not last_resort:
            log.write( "sshd is already running\n" )

    if last_resort:
        # this will make the initial script stop requesting scripts from PLC
        utils.sysexec( "touch %s" % cancel_boot_flag, log )

    # for ease of use, setup lvm on 2.x cds
    if BOOT_CD_VERSION[0] == 2:
        compatibility.setup_lvm_2x_cd(vars,log)

    if last_resort:
        print warning_message
    
    return
