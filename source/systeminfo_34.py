#!/usr/bin/python2

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.
# expected /proc/partitions format


#----------------------------------------------------
#major minor  #blocks  name
#
#3     0   40017915 hda
#3     1     208813 hda1
#3     2   20482875 hda2
#3     3     522112 hda3
#3     4   18804082 hda4
#----------------------------------------------------


import string
import sys
import os
import popen2
import re
import errno
import ModelOptions
import pypciscan
import pypcimap
from Exceptions import *

"""
a utility class for finding and returning information about
block devices, memory, and other hardware on the system
"""

PROC_MEMINFO_PATH= "/proc/meminfo"
PROC_PARTITIONS_PATH= "/proc/partitions"

# set when the sfdisk -l <dev> trick has been done to make
# all devices show up
DEVICES_SCANNED_FLAG= "/tmp/devices_scanned"

# a /proc/partitions block is 1024 bytes
# a GB to a HDD manufacturer is 10^9 bytes
BLOCKS_PER_GB = pow(10, 9) / 1024.0;


# -n is numeric ids (no lookup), -m is machine readable
LSPCI_CMD= "/sbin/lspci -nm"

MODULE_CLASS_NETWORK= "network"
MODULE_CLASS_SCSI= "scsi"

PCI_BASE_CLASS_NETWORK=0x02L
PCI_BASE_CLASS_STORAGE=0x01L

PCI_ANY=0xffffffffL

def get_total_phsyical_mem(vars = {}, log = sys.stderr):
    """
    return the total physical memory of the machine, in kilobytes.

    Return None if /proc/meminfo not readable.
    """

    try:
        meminfo_file= file(PROC_MEMINFO_PATH,"r")
    except IOError, e:
        return

    total_memory= None

    for line in meminfo_file:

        try:
            (fieldname,value)= string.split(line,":")
        except ValueError, e:
            # this will happen for lines that don't have two values
            # (like the first line on 2.4 kernels)
            continue

        fieldname= string.strip(fieldname)
        value= string.strip(value)
        
        if fieldname == "MemTotal":
            try:
                (total_memory,units)= string.split(value)
            except ValueError, e:
                return

            if total_memory == "" or total_memory == None or \
                   units == "" or units == None:
                return

            if string.lower(units) != "kb":
                return

            try:
                total_memory= int(total_memory)
            except ValueError, e:
                return

            break

    meminfo_file.close()
    return total_memory

def get_block_device_list(vars = {}, log = sys.stderr):
    """
    get a list of block devices from this system.
    return an associative array, where the device name
    (full /dev/device path) is the key, and the value
    is a tuple of (major,minor,numblocks,gb_size,readonly)
    """

    # make sure we can access to the files/directories in /proc
    if not os.access(PROC_PARTITIONS_PATH, os.F_OK):
        return None

    # table with valid scsi/sata/ide/raid block device names
    valid_blk_names = {}
    # add in valid sd and hd block device names
    for blk_prefix in ('sd','hd'):
        for blk_num in map ( \
            lambda x: chr(x), range(ord('a'),ord('z')+1)):
            devicename="%s%c" % (blk_prefix, blk_num)
            valid_blk_names[devicename]=None

    # add in valid scsi raid block device names
    for M in range(0,1+1):
        for N in range(0,7+1):
            devicename = "cciss/c%dd%d" % (M,N)
            valid_blk_names[devicename]=None

    for devicename in valid_blk_names.keys():
        # devfs under 2.4 (old boot cds) used to list partitions
        # in a format such as scsi/host0/bus0/target0/lun0/disc
        # and /dev/sda, etc. were just symlinks
        try:
            devfsname= os.readlink( "/dev/%s" % devicename )
            valid_blk_names[devfsname]=None
        except OSError:
            pass

    # only do this once every system boot
    if not os.access(DEVICES_SCANNED_FLAG, os.R_OK):

        # this is ugly. under devfs, device
        # entries in /dev/scsi/.. and /dev/ide/...
        # don't show up until you attempt to read
        # from the associated device at /dev (/dev/sda).
        # so, lets run sfdisk -l (list partitions) against
        # most possible block devices, that way they show
        # up when it comes time to do the install.
        devicenames = valid_blk_names.keys()
        devicenames.sort()
        for devicename in devicenames:
            os.system( "sfdisk -l /dev/%s > /dev/null 2>&1" % devicename )

        # touch file
        fb = open(DEVICES_SCANNED_FLAG,"w")
        fb.close()

    devicelist= {}

    partitions_file= file(PROC_PARTITIONS_PATH,"r")
    line_count= 0
    for line in partitions_file:
        line_count= line_count + 1

        # skip the first two lines always
        if line_count < 2:
            continue

        parts= string.split(line)

        if len(parts) < 4:
            continue

        device= parts[3]

        # skip and ignore any partitions
        if not valid_blk_names.has_key(device):
            continue

        try:
            major= int(parts[0])
            minor= int(parts[1])
            blocks= int(parts[2])
        except ValueError, err:
            continue

        gb_size= blocks/BLOCKS_PER_GB

        # check to see if the blk device is readonly
        try:
            # can we write to it?
            dev_name= "/dev/%s" % device
            fb = open(dev_name,"w")
            fb.close()
            readonly=False
        except IOError, e:
            # check if EROFS errno
            if errno.errorcode.get(e.errno,None) == 'EROFS':
                readonly=True
            else:
                # got some other errno, pretend device is readonly
                readonly=True

        devicelist[dev_name]= (major,minor,blocks,gb_size,readonly)

    return devicelist


def get_system_modules( vars = {}, log = sys.stderr):
    """
    Return a list of kernel modules that this system requires.
    This requires access to the installed system's root
    directory, as the following file must exist and is used:
    <install_root>/lib/modules/(first entry if kernel_version unspecified)/modules.pcimap

    If there are more than one kernels installed, and the kernel
    version is not specified, then only the first one in
    /lib/modules is used.

    Returns a dictionary, keys being the type of module:
        - scsi       MODULE_CLASS_SCSI
        - network    MODULE_CLASS_NETWORK
    The value being the kernel module name to load.

    Some sata devices show up under an IDE device class,
    hence the reason for checking for ide devices as well.
    If there actually is a match in the pci -> module lookup
    table, and its an ide device, its most likely sata,
    as ide modules are built in to the kernel.
    """

    if not vars.has_key("SYSIMG_PATH"):
        vars["SYSIMG_PATH"]="/"
    SYSIMG_PATH=vars["SYSIMG_PATH"]

    if not vars.has_key("NODE_MODEL_OPTIONS"):
        vars["NODE_MODEL_OPTIONS"] = 0;

    initrd, kernel_version = getKernelVersion(vars, log)

    # get the kernel version we are assuming
    if kernel_version is None:
        try:
            kernel_version= os.listdir( "%s/lib/modules/" % SYSIMG_PATH )
        except OSError, e:
            return

        if len(kernel_version) == 0:
            return

        if len(kernel_version) > 1:
            print( "WARNING: We may be returning modules for the wrong kernel." )

        kernel_version= kernel_version[0]

    print( "Using kernel version %s" % kernel_version )

    # test to make sure the file we need is present
    modules_pcimap_path = "%s/lib/modules/%s/modules.pcimap" % \
                          (SYSIMG_PATH,kernel_version)
    if not os.access(modules_pcimap_path,os.R_OK):
        print( "Unable to read %s" % path )
        return

    pcimap = pypcimap.PCIMap(modules_pcimap_path)

    # this is the actual data structure we return
    system_mods= {}

    # these are the lists that will be in system_mods
    network_mods= []
    scsi_mods= []

    # XXX: this is really similar to what BootCD/conf_files/pl_hwinit does. merge?
    pcidevs = pypciscan.get_devices()

    for (slot, dev) in pcidevs.iteritems():
        base = (dev[4] & 0xff0000) >> 16
        if base not in (PCI_BASE_CLASS_STORAGE,
                        PCI_BASE_CLASS_NETWORK):
            continue

        modules = pcimap.get(dev)
        if len(modules) > 0:
            if base == PCI_BASE_CLASS_NETWORK:
                network_mods += modules
            elif base == PCI_BASE_CLASS_STORAGE:
                scsi_mods += modules

    system_mods[MODULE_CLASS_SCSI]= scsi_mods
    system_mods[MODULE_CLASS_NETWORK]= network_mods

    return system_mods


def getKernelVersion( vars = {} , log = sys.stderr):
    # make sure we have the variables we need
    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        NODE_MODEL_OPTIONS=vars["NODE_MODEL_OPTIONS"]
    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

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
            option = ''
    try:
        initrd= os.readlink( "%s/boot/initrd-boot%s" % (SYSIMG_PATH,option) )
        kernel_version= initrd.replace("initrd-", "").replace(".img", "")    
    except OSError, e:
        initrd = None
        kernel_version = None
        
    return (initrd, kernel_version)


if __name__ == "__main__":
    devices= get_block_device_list()
    print "block devices detected:"
    if not devices:
        print "no devices found!"
    else:
        for dev in devices.keys():
            print "%s %s" % (dev, repr(devices[dev]))
            

    print ""
    memory= get_total_phsyical_mem()
    if not memory:
        print "unable to read /proc/meminfo for memory"
    else:
        print "total physical memory: %d kb" % memory
        

    print ""

    kernel_version = None
    if len(sys.argv) > 2:
        kernel_version = sys.argv[1]
        
    modules= get_system_modules()
    if not modules:
        print "unable to list system modules"
    else:
        for type in modules:
            if type == MODULE_CLASS_SCSI:
                print( "all scsi modules:" )
                for a_mod in modules[type]:
                    print a_mod
            elif type == MODULE_CLASS_NETWORK:
                print( "all network modules:" )
                for a_mod in modules[type]:
                    print a_mod
                
