#!/usr/bin/python2 -u

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import os, string

from Exceptions import *
import utils
import systeminfo
import BootAPI
import ModelOptions
import notify_messages

def Run( vars, log, filename = "/etc/modprobe.conf"):
    """
    write out the system file /etc/modprobe.conf with the current
    set of modules.

    returns a tuple of the number of network driver lines and storage
    driver lines written as (networkcount,storagecount)
    """

    # write out the modprobe.conf file for the system. make sure
    # the order of the ethernet devices are listed in the same order
    # as the boot cd loaded the modules. this is found in /tmp/loadedmodules
    # ultimately, the order will only match the boot cd order if
    # the kernel modules have the same name - which should be true for the later
    # version boot cds because they use the same kernel version.
    # older boot cds use a 2.4.19 kernel, and its possible some of the network
    # module names have changed, in which case the system might not boot
    # if the network modules are activated in a different order that the
    # boot cd.

    # make sure we have this class loaded
    
    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    sysmods= systeminfo.get_system_modules(vars, log)
    if sysmods is None:
        raise BootManagerException, "Unable to get list of system modules."
        
    modulesconf_file= file("%s/%s" % (SYSIMG_PATH,filename), "w" )
    modulesconf_file.write("options ata_generic all_generic_ide=1\n")

    # MEF: I am not sure this is the proper thing to do if there are
    # two completely different scsi_hostadapter.  I think its ok, but
    # it seems rather arbitrary.
    count=0
    for a_mod in sysmods[systeminfo.MODULE_CLASS_SCSI]:
        line="alias scsi_hostadapter%d %s\n" % (count,a_mod) 
        modulesconf_file.write(line)
        count=count+1

    # This should involve looking at the NodeNetworks associated with
    # this node and matching on their ethernet address.  Barring that
    # information order the remaining ethX numbering according to PCI
    # enumeration order. This should be integrated with
    # WriteNetworkConfig and integrate.  For now lets just comment out
    # the 'alias ethX a_mod' lines in modprobe.conf
    count=0
    for a_mod in sysmods[systeminfo.MODULE_CLASS_NETWORK]:
        line="alias eth%d %s # Want to comment this out in the future.\n" % (count,a_mod) 
        modulesconf_file.write(line)
        count=count+1

    modulesconf_file.close()
    modulesconf_file= None

    # dump the modprobe.conf file to the log (not to screen)
    log.write( "Contents of new modprobe.conf file:\n" )
    modulesconf_file= file("%s/%s" % (SYSIMG_PATH,filename), "r" )
    contents= modulesconf_file.read()
    log.write( contents + "\n" )
    modulesconf_file.close()
    modulesconf_file= None
    log.write( "End contents of new modprobe.conf file.\n" )

    # before we do the real kexec, check to see if we had any
    # network drivers written to modprobe.conf. if not, return -1,
    # which will cause this node to be switched to a debug state.
    scsi_count=len(sysmods[systeminfo.MODULE_CLASS_SCSI])
    eth_count=len(sysmods[systeminfo.MODULE_CLASS_NETWORK])
    if eth_count == 0:
        log.write( "\nIt appears we don't have any network drivers. Aborting.\n" )
        
        vars['BOOT_STATE']= 'failboot'
        vars['STATE_CHANGE_NOTIFY']= 1
        vars['STATE_CHANGE_NOTIFY_MESSAGE']= \
             notify_messages.MSG_NO_DETECTED_NETWORK
        raise BootManagerException, \
              notify_messages.MSG_NO_DETECTED_NETWORK


