#!/usr/bin/python

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import string

import InstallPartitionDisks
from Exceptions import *
import systeminfo
import utils
import os

import ModelOptions


def Run( vars, log ):
    """
    Find any new large block devices we can add to the vservers volume group
    
    Expect the following variables to be set:
    SYSIMG_PATH          the path where the system image will be mounted
    MINIMUM_DISK_SIZE       any disks smaller than this size, in GB, are not used
    NODE_MODEL_OPTIONS   the node's model options
    
    Set the following variables upon successfully running:
    ROOT_MOUNTED             the node root file system is mounted
    """

    log.write( "\n\nStep: Checking for unused disks to add to LVM.\n" )

    # make sure we have the variables we need
    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        MINIMUM_DISK_SIZE= int(vars["MINIMUM_DISK_SIZE"])

        PARTITIONS= vars["PARTITIONS"]
        if PARTITIONS == None:
            raise ValueError, "PARTITIONS"
        
        NODE_MODEL_OPTIONS= vars["NODE_MODEL_OPTIONS"]
    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    all_devices= systeminfo.get_block_device_list(vars, log)
    
    # will contain the new devices to add to the volume group
    new_devices= []

    # total amount of new space in gb
    extended_gb_size= 0
    
    for device in all_devices.keys():

        (major,minor,blocks,gb_size,readonly)= all_devices[device]

        if device[:14] == "/dev/planetlab":
            log.write( "Skipping device %s in volume group.\n" % device )
            continue

        if readonly:
            log.write( "Skipping read only device %s\n" % device )
            continue

        if gb_size < MINIMUM_DISK_SIZE:
            log.write( "Skipping too small device %s (%4.2f)\n" %
                       (device,gb_size) )
            continue

        log.write( "Checking device %s to see if it is part " \
                   "of the volume group.\n" % device )

        # this is the lvm partition, if it exists on that device
        lvm_partition= InstallPartitionDisks.get_partition_path_from_device( device, vars, log )
        cmd = "pvdisplay %s | grep -q 'planetlab'" % lvm_partition
        already_added= utils.sysexec_noerr(cmd, log)

        if already_added:
            log.write( "It appears %s is part of the volume group, continuing.\n" %
                       device )
            continue

        # just to be extra paranoid, ignore the device if it already has
        # an lvm partition on it (new disks won't have this, and that is
        # what this code is for, so it should be ok).
        cmd = "sfdisk -l %s | grep -q 'Linux LVM'" % device 
        has_lvm= utils.sysexec_noerr(cmd, log)
        if has_lvm:
            log.write( "It appears %s has lvm already setup on it.\n" % device)
            paranoid = False
            if paranoid:
                log.write("To paranoid to add %s to vservers lvm.\n" % device)
                continue
        
        if not InstallPartitionDisks.single_partition_device( device, vars, log ):
            log.write( "Unable to partition %s, not using it.\n" % device )
            continue

        log.write( "Successfully partitioned %s\n" % device )

        if NODE_MODEL_OPTIONS & ModelOptions.RAWDISK:
            log.write( "Running on a raw disk node, not using it.\n" )
            continue

        part_path= InstallPartitionDisks.get_partition_path_from_device( device,
                                                                         vars, log )

        log.write( "Attempting to add %s to the volume group\n" % device )

        if not InstallPartitionDisks.create_lvm_physical_volume( part_path,
                                                                 vars, log ):
            log.write( "Unable to create lvm physical volume %s, not using it.\n" %
                       part_path )
            continue

        log.write( "Adding %s to list of devices to add to " \
                   "planetlab volume group.\n" % device )

        extended_gb_size= extended_gb_size + gb_size
        new_devices.append( part_path )
        

    if len(new_devices) > 0:

        log.write( "Extending planetlab volume group.\n" )
        
        log.write( "Unmounting disks.\n" )
        try:
            # backwards compat, though, we should never hit this case post PL 3.2
            os.stat("%s/rcfs/taskclass"%SYSIMG_PATH)
            utils.sysexec_chroot_noerr( SYSIMG_PATH, "umount /rcfs", log )
        except OSError, e:
            pass

        # umount in order to extend disk size
        utils.sysexec_noerr( "umount %s/proc" % SYSIMG_PATH, log )
        utils.sysexec_noerr( "umount %s/vservers" % SYSIMG_PATH, log )
        utils.sysexec_noerr( "umount %s" % SYSIMG_PATH, log )
        utils.sysexec( "vgchange -an", log )
        
        vars['ROOT_MOUNTED']= 0

        while True:
            cmd = "vgextend planetlab %s" % string.join(new_devices," ")
            if not utils.sysexec_noerr( cmd, log ):
                log.write( "Failed to add physical volumes %s to " \
                           "volume group, continuing.\n" % string.join(new_devices," "))
                res = 1
                break
            
            # now, get the number of unused extents, and extend the vserver
            # logical volume by that much.
            remaining_extents= \
               InstallPartitionDisks.get_remaining_extents_on_vg( vars, log )

            log.write( "Extending vservers logical volume.\n" )
            utils.sysexec( "vgchange -ay", log )
            cmd = "lvextend -l +%s %s" % (remaining_extents, PARTITIONS["vservers"])
            if not utils.sysexec_noerr(cmd, log):
                log.write( "Failed to extend vservers logical volume, continuing\n" )
                res = 1
                break

            log.write( "making the ext3 filesystem match new logical volume size.\n" )

            vars['ROOT_MOUNTED']= 1
            cmd = "mount %s %s" % (PARTITIONS["root"],SYSIMG_PATH)
            utils.sysexec_noerr( cmd, log )
            cmd = "mount %s %s/vservers" % \
                (PARTITIONS["vservers"],SYSIMG_PATH)
            utils.sysexec_noerr( cmd, log )
            cmd = "ext2online %s/vservers" % SYSIMG_PATH
            resize = utils.sysexec_noerr(cmd,log)
            utils.sysexec_noerr( "umount %s/vservers" % SYSIMG_PATH, log )
            utils.sysexec_noerr( "umount %s" % SYSIMG_PATH, log )
            vars['ROOT_MOUNTED']= 0

            utils.sysexec( "vgchange -an", log )

            if not resize:
                log.write( "Failed to resize vservers partition, continuing.\n" )
                res = 1
                break
            else:
                log.write( "Extended vservers partition by %4.2f GB\n" %
                           extended_gb_size )
                res = 1
                break

    else:
        log.write( "No new disk devices to add to volume group.\n" )
        res = 1

    return res
