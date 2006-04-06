import string

import InstallPartitionDisks
from Exceptions import *
from systeminfo import systeminfo
import compatibility
import utils
import os


def Run( vars, log ):
    """
    Find any new large block devices we can add to the vservers volume group
    
    Expect the following variables to be set:
    SYSIMG_PATH          the path where the system image will be mounted
    BOOT_CD_VERSION          A tuple of the current bootcd version
    MINIMUM_DISK_SIZE       any disks smaller than this size, in GB, are not used
    
    Set the following variables upon successfully running:
    ROOT_MOUNTED             the node root file system is mounted
    """

    log.write( "\n\nStep: Checking for unused disks to add to LVM.\n" )

    # make sure we have the variables we need
    try:
        BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        if BOOT_CD_VERSION == "":
            raise ValueError, "BOOT_CD_VERSION"

        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        MINIMUM_DISK_SIZE= int(vars["MINIMUM_DISK_SIZE"])
        
    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    sysinfo= systeminfo()

    all_devices= sysinfo.get_block_device_list()
    
    # find out if there are unused disks in all_devices that are greater
    # than old cds need extra utilities to run lvm
    if BOOT_CD_VERSION[0] == 2:
        compatibility.setup_lvm_2x_cd( vars, log )
        
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
        lvm_partition= "%s1" % device
        already_added= utils.sysexec_noerr( "pvdisplay %s | grep -q 'planetlab'" %
                                            lvm_partition )
        
        if already_added:
            log.write( "It appears %s is part of the volume group, continuing.\n" %
                       device )
            continue

        # just to be extra paranoid, ignore the device if it already has
        # an lvm partition on it (new disks won't have this, and that is
        # what this code is for, so it should be ok).
        has_lvm= utils.sysexec_noerr( "sfdisk -l %s | grep -q 'Linux LVM'" %
                                      device )
        if has_lvm:
            log.write( "It appears %s has/had lvm already setup on "\
                       "it, continuing.\n" % device )
            continue
        

        log.write( "Attempting to add %s to the volume group\n" % device )

        if not InstallPartitionDisks.single_partition_device( device, vars, log ):
            log.write( "Unable to partition %s, not using it.\n" % device )
            continue

        log.write( "Successfully initialized %s\n" % device )

        part_path= InstallPartitionDisks.get_partition_path_from_device( device,
                                                                         vars, log )
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
            utils.sysexec_noerr( "chroot %s umount /rcfs" % SYSIMG_PATH, log )
        except OSError, e:
            pass

        utils.sysexec_noerr( "umount /dev/planetlab/vservers", log )
        utils.sysexec_noerr( "umount /dev/planetlab/root", log )
        utils.sysexec( "vgchange -an", log )
        
        vars['ROOT_MOUNTED']= 0

        if not utils.sysexec_noerr( "vgextend planetlab %s" %
                                    string.join(new_devices," "), log ):
            log.write( "Failed to add physical volumes %s to " \
                       "volume group, continuing.\n" % string.join(new_devices," "))
            return 1

        # now, get the number of unused extents, and extend the vserver
        # logical volume by that much.
        remaining_extents= \
               InstallPartitionDisks.get_remaining_extents_on_vg( vars, log )

        log.write( "Extending vservers logical volume.\n" )
        
        if not utils.sysexec_noerr("lvextend -l +%s /dev/planetlab/vservers" %
                                   remaining_extents, log):
            log.write( "Failed to extend vservers logical volume, continuing\n" )
            return 1

        log.write( "making the ext3 filesystem match new logical volume size.\n" )
        if not utils.sysexec_noerr("resize2fs /dev/planetlab/vservers",log):
            log.write( "Failed to make ext3 file system match, continuing\n" )
            return 1
            
        log.write( "Succesfully extended vservers partition by %4.2f GB\n" %
                   extended_gb_size )
    else:
        log.write( "No new disk devices to add to volume group.\n" )

    return 1
