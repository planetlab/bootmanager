# Copyright (c) 2003 Intel Corporation
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.

#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.

#     * Neither the name of the Intel Corporation nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE INTEL OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# EXPORT LAWS: THIS LICENSE ADDS NO RESTRICTIONS TO THE EXPORT LAWS OF
# YOUR JURISDICTION. It is licensee's responsibility to comply with any
# export regulations applicable in licensee's jurisdiction. Under
# CURRENT (May 2000) U.S. export regulations this software is eligible
# for export from the U.S. and can be downloaded by or otherwise
# exported or reexported worldwide EXCEPT to U.S. embargoed destinations
# which include Cuba, Iraq, Libya, North Korea, Iran, Syria, Sudan,
# Afghanistan and any other country to which the U.S. has embargoed
# goods and services.


import os, sys
import string
import popen2


from Exceptions import *
import utils
import BootServerRequest
import compatibility



def Run( vars, log ):
    """
    Setup the block devices for install, partition them w/ LVM
    
    Expect the following variables from the store:
    INSTALL_BLOCK_DEVICES    list of block devices to install onto
    TEMP_PATH                somewhere to store what we need to run
    ROOT_SIZE                the size of the root logical volume
    SWAP_SIZE                the size of the swap partition
    ALPINA_SERVER_DIR        directory on the boot servers containing alpina
                             scripts and support files
    BOOT_CD_VERSION          A tuple of the current bootcd version
    
    Sets the following variables:
    PARTITIONS               diction of generic part. types (root/swap)
                             and their associated devices.
                             Current keys/values:
                                 root    /dev/planetlab/root
                                 swap    /dev/planetlab/swap
    
    """

    log.write( "\n\nStep: Install: partitioning disks.\n" )
        
    # make sure we have the variables we need
    try:
        TEMP_PATH= vars["TEMP_PATH"]
        if TEMP_PATH == "":
            raise ValueError, "TEMP_PATH"

        INSTALL_BLOCK_DEVICES= vars["INSTALL_BLOCK_DEVICES"]
        if( len(INSTALL_BLOCK_DEVICES) == 0 ):
            raise ValueError, "INSTALL_BLOCK_DEVICES is empty"

        ROOT_SIZE= vars["ROOT_SIZE"]
        if ROOT_SIZE == "" or ROOT_SIZE == 0:
            raise ValueError, "ROOT_SIZE invalid"

        SWAP_SIZE= vars["SWAP_SIZE"]
        if SWAP_SIZE == "" or SWAP_SIZE == 0:
            raise ValueError, "SWAP_SIZE invalid"

        ALPINA_SERVER_DIR= vars["ALPINA_SERVER_DIR"]
        if ALPINA_SERVER_DIR == None:
            raise ValueError, "ALPINA_SERVER_DIR"

        BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        if BOOT_CD_VERSION == "":
            raise ValueError, "BOOT_CD_VERSION"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    bs_request= BootServerRequest.BootServerRequest()

    
    # old cds need extra utilities to partition disks and setup lvm
    if BOOT_CD_VERSION[0] == 2:
        compatibility.setup_partdisks_2x_cd( vars, log )

    import parted
        
    # define the basic partition paths
    PARTITIONS= {}
    PARTITIONS["root"]= "/dev/planetlab/root"
    PARTITIONS["swap"]= "/dev/planetlab/swap"
    PARTITIONS["vservers"]= "/dev/planetlab/vservers"
    # Linux 2.6 mounts LVM with device mapper
    PARTITIONS["mapper-root"]= "/dev/mapper/planetlab-root"
    PARTITIONS["mapper-swap"]= "/dev/mapper/planetlab-swap"
    PARTITIONS["mapper-vservers"]= "/dev/mapper/planetlab-vservers"
    vars["PARTITIONS"]= PARTITIONS

    
    # disable swap if its on
    utils.sysexec_noerr( "swapoff %s" % PARTITIONS["swap"], log )

    # shutdown and remove any lvm groups/volumes
    utils.sysexec_noerr( "vgscan", log )
    utils.sysexec_noerr( "vgchange -ay", log )        
    utils.sysexec_noerr( "lvremove -f /dev/planetlab/root", log )
    utils.sysexec_noerr( "lvremove -f /dev/planetlab/swap", log )
    utils.sysexec_noerr( "lvremove -f /dev/planetlab/vservers", log )
    utils.sysexec_noerr( "vgchange -an", log )
    utils.sysexec_noerr( "vgremove planetlab", log )

    log.write( "Running vgscan for devices\n" )
    utils.sysexec_noerr( "vgscan", log )
    
    used_devices= []

    for device in INSTALL_BLOCK_DEVICES:

        if single_partition_device( device, vars, log ):
            used_devices.append( device )
            log.write( "Successfully initialized %s\n" % device )
        else:
            log.write( "Unable to partition %s, not using it.\n" % device )
            continue

    # list of devices to be used with vgcreate
    vg_device_list= ""

    # initialize the physical volumes
    for device in used_devices:

        part_path= get_partition_path_from_device( device, vars, log )
        
        if not create_lvm_physical_volume( part_path, vars, log ):
            raise BootManagerException, "Could not create lvm physical volume " \
                  "on partition %s" % part_path
        
        vg_device_list = vg_device_list + " " + part_path

    # create an lvm volume group
    utils.sysexec( "vgcreate -s32M planetlab %s" % vg_device_list, log)

    # create swap logical volume
    utils.sysexec( "lvcreate -L%s -nswap planetlab" % SWAP_SIZE, log )

    # create root logical volume
    utils.sysexec( "lvcreate -L%s -nroot planetlab" % ROOT_SIZE, log )

    # create vservers logical volume with all remaining space
    # first, we need to get the number of remaining extents we can use
    remaining_extents= get_remaining_extents_on_vg( vars, log )
    
    utils.sysexec( "lvcreate -l%s -nvservers planetlab" % remaining_extents, log )

    # activate volume group (should already be active)
    #utils.sysexec( TEMP_PATH + "vgchange -ay planetlab", log )

    # make swap
    utils.sysexec( "mkswap %s" % PARTITIONS["swap"], log )

    # make root file system
    utils.sysexec( "mkfs.ext2 -j %s" % PARTITIONS["root"], log )

    # make vservers file system
    utils.sysexec( "mkfs.ext2 -m 0 -j %s" % PARTITIONS["vservers"], log )

    # save the list of block devices in the log
    log.write( "Block devices used (in lvm):\n" )
    log.write( repr(used_devices) + "\n" )
    log.write( "End of block devices used (in lvm).\n" )

    # list of block devices used may be updated
    vars["INSTALL_BLOCK_DEVICES"]= used_devices

    return 1



def single_partition_device( device, vars, log ):
    """
    initialize a disk by removing the old partition tables,
    and creating a new single partition that fills the disk.

    return 1 if sucessful, 0 otherwise
    """

    BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
    if BOOT_CD_VERSION[0] == 2:
        compatibility.setup_partdisks_2x_cd( vars, log )

    import parted
    
    lvm_flag= parted.partition_flag_get_by_name('lvm')
    
    try:
        # wipe the old partition table
        utils.sysexec( "dd if=/dev/zero of=%s bs=512 count=1" % device, log )

        # get the device
        dev= parted.PedDevice.get(device)

        # 2.x cds have different libparted that 3.x cds, and they have
        # different interfaces
        if BOOT_CD_VERSION[0] == 3:

            # create a new partition table
            disk= dev.disk_new_fresh(parted.disk_type_get("msdos"))

            # create one big partition on each block device
            constraint= dev.constraint_any()

            new_part= disk.partition_new(
                parted.PARTITION_PRIMARY,
                parted.file_system_type_get("ext2"),
                0, 1 )

            # make it an lvm partition
            new_part.set_flag(lvm_flag,1)

            # actually add the partition to the disk
            disk.add_partition(new_part, constraint)

            disk.maximize_partition(new_part,constraint)

            disk.commit()
            del disk
        else:
            # create a new partition table
            dev.disk_create(parted.disk_type_get("msdos"))

            # get the disk
            disk= parted.PedDisk.open(dev)

                # create one big partition on each block device
            part= disk.next_partition()
            while part:
                if part.type == parted.PARTITION_FREESPACE:
                    new_part= disk.partition_new(
                        parted.PARTITION_PRIMARY,
                        parted.file_system_type_get("ext2"),
                        part.geom.start,
                        part.geom.end )

                    constraint = disk.constraint_any()

                    # make it an lvm partition
                    new_part.set_flag(lvm_flag,1)

                    # actually add the partition to the disk
                    disk.add_partition(new_part, constraint)

                    break

                part= disk.next_partition(part)

            disk.write()
            disk.close()
            del disk
            
    except BootManagerException, e:
        log.write( "BootManagerException while running: %s\n" % str(e) )
        return 0

    except parted.error, e:
        log.write( "parted exception while running: %s\n" % str(e) )
        return 0
                   
    return 1



def create_lvm_physical_volume( part_path, vars, log ):
    """
    make the specificed partition a lvm physical volume.

    return 1 if successful, 0 otherwise.
    """

    try:
        # again, wipe any old data, this time on the partition
        utils.sysexec( "dd if=/dev/zero of=%s bs=512 count=1" % part_path, log )
        utils.sysexec( "pvcreate -fy %s" % part_path, log )
    except BootManagerException, e:
        log.write( "create_lvm_physical_volume failed.\n" )
        return 0

    return 1



def get_partition_path_from_device( device, vars, log ):
    """
    given a device, return the path of the first partition on the device
    """

    BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        
    # those who wrote the cciss driver just had to make it difficult
    if BOOT_CD_VERSION[0] == 3:
        cciss_test= "/dev/cciss"
        if device[:len(cciss_test)] == cciss_test:
            part_path= device + "p1"
        else:
            part_path= device + "1"
    else:
        # since device ends in /disc, we need to make it end in
        # /part1 to indicate the first partition (for devfs based 2.x cds)
        dev_parts= string.split(device,"/")
        dev_parts[len(dev_parts)-1]= "part1"
        part_path= string.join(dev_parts,"/")

    return part_path



def get_remaining_extents_on_vg( vars, log ):
    """
    return the free amount of extents on the planetlab volume group
    """
    
    c_stdout, c_stdin = popen2.popen2("vgdisplay -c planetlab")
    result= string.strip(c_stdout.readline())
    c_stdout.close()
    c_stdin.close()
    remaining_extents= string.split(result,":")[15]
    
    return remaining_extents
