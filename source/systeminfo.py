#!/usr/bin/python2

# --------------
# THIS file used to be named 'blockdevicescan.py', but has been renamed
# systeminfo.py and made more generic (now includes info about memory,
# and other hardware info on the machine)
# --------------

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


# expected /proc/partitions format
#
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
import os
import popen2
from merge_hw_tables import merge_hw_tables


class systeminfo:
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

    PCI_CLASS_NETWORK= "0200"
    PCI_CLASS_RAID= "0104"
    PCI_CLASS_RAID2= "0100"
    PCI_CLASS_IDE= "0101"

    def get_total_phsyical_mem(self):
        """
        return the total physical memory of the machine, in kilobytes.

        Return None if /proc/meminfo not readable.
        """
        
        try:
            meminfo_file= file(self.PROC_MEMINFO_PATH,"r")
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



    def get_block_device_list(self):
        """
        get a list of block devices from this system.
        return an associative array, where the device name
        (full /dev/device path) is the key, and the value
        is a tuple of (major,minor,numblocks,gb_size,readonly)
        """
        
        # make sure we can access to the files/directories in /proc
        if not os.access(self.PROC_PARTITIONS_PATH, os.F_OK):
            return None


        # only do this once every system boot
        if not os.access(self.DEVICES_SCANNED_FLAG, os.R_OK):
            
            # this is ugly. under devfs, device
            # entries in /dev/scsi/.. and /dev/ide/...
            # don't show up until you attempt to read
            # from the associated device at /dev (/dev/sda).
            # so, lets run sfdisk -l (list partitions) against
            # most possible block devices, that way they show
            # up when it comes time to do the install.
            for dev_prefix in ('sd','hd'):
                block_dev_num= 0
                while block_dev_num < 10:
                    if block_dev_num < 26:
                        devicename= "/dev/%s%c" % \
                                    (dev_prefix, chr(ord('a')+block_dev_num))
                    else:
                        devicename= "/dev/%s%c%c" % \
                                    ( dev_prefix,
                                      chr(ord('a')+((block_dev_num/26)-1)),
                                      chr(ord('a')+(block_dev_num%26)) )

                    os.system( "sfdisk -l %s > /dev/null 2>&1" % devicename )
                    block_dev_num = block_dev_num + 1

            additional_scan_devices= ("/dev/cciss/c0d0p", "/dev/cciss/c0d1p",
                                      "/dev/cciss/c0d2p", "/dev/cciss/c0d3p",
                                      "/dev/cciss/c0d4p", "/dev/cciss/c0d5p",
                                      "/dev/cciss/c0d6p", "/dev/cciss/c0d7p",
                                      "/dev/cciss/c1d0p", "/dev/cciss/c1d1p",
                                      "/dev/cciss/c1d2p", "/dev/cciss/c1d3p",
                                      "/dev/cciss/c1d4p", "/dev/cciss/c1d5p",
                                      "/dev/cciss/c1d6p", "/dev/cciss/c1d7p",)
            
            for devicename in additional_scan_devices:
                os.system( "sfdisk -l %s > /dev/null 2>&1" % devicename )

            os.system( "touch %s" % self.DEVICES_SCANNED_FLAG )
            

        devicelist= {}

        partitions_file= file(self.PROC_PARTITIONS_PATH,"r")
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

            # if the last char in device is a number, its
            # a partition, and we ignore it
            
            if device[len(device)-1].isdigit():
                continue

            dev_name= "/dev/%s" % device
            
            try:
                major= int(parts[0])
                minor= int(parts[1])
                blocks= int(parts[2])
            except ValueError, err:
                continue

            gb_size= blocks/self.BLOCKS_PER_GB
            
            # parse the output of hdparm <disk> to get the readonly flag;
            # if this fails, assume it isn't read only
            readonly= 0
            
            hdparm_cmd = popen2.Popen3("hdparm %s 2> /dev/null" % dev_name)
            status= hdparm_cmd.wait()

            if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0:
                try:
                    hdparm_output= hdparm_cmd.fromchild.read()
                    hdparm_cmd= None
                    
                    # parse the output of hdparm, the lines we are interested
                    # in look
                    # like:
                    #
                    #  readonly     =  0 (off)
                    #
                    
                    for line in string.split(hdparm_output,"\n"):
                        
                        line= string.strip(line)
                        if line == "":
                            continue
                        
                        line_parts= string.split(line,"=")
                        if len(line_parts) < 2:
                            continue

                        name= string.strip(line_parts[0])

                        if name == "readonly":
                            value= string.strip(line_parts[1])
                            if len(value) == 0:
                                break

                            if value[0] == "1":
                                readonly= 1
                                break

                except IOError:
                    pass

            devicelist[dev_name]= (major,minor,blocks,gb_size,readonly)

            
        return devicelist



    def get_system_modules( self, install_root ):
        """
        Return a list of kernel modules that this system requires.
        This requires access to the installed system's root
        directory, as the following files must exist and are used:
        <install_root>/usr/share/hwdata/pcitable
        <install_root>/lib/modules/(first entry)/modules.pcimap
        <install_root>/lib/modules/(first entry)/modules.dep

        Note, that this assumes there is only one kernel
        that is installed. If there are more than one, then
        only the first one in a directory listing is used.

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

        # get the kernel version we are assuming
        try:
            kernel_version= os.listdir( "%s/lib/modules/" % install_root )
        except OSError, e:
            return

        if len(kernel_version) == 0:
            return

        if len(kernel_version) > 1:
            print( "WARNING: We may be returning modules for the wrong kernel." )

        kernel_version= kernel_version[0]
        print( "Using kernel version %s" % kernel_version )

        # test to make sure the three files we need are present
        pcitable_path = "%s/usr/share/hwdata/pcitable" % install_root
        modules_pcimap_path = "%s/lib/modules/%s/modules.pcimap" % \
                              (install_root,kernel_version)
        modules_dep_path = "%s/lib/modules/%s/modules.dep" % \
                           (install_root,kernel_version)

        for path in (pcitable_path,modules_pcimap_path,modules_dep_path):
            if not os.access(path,os.R_OK):
                print( "Unable to read %s" % path )
                return

        # now, with those three files, merge them all into one easy to
        # use lookup table
        all_modules= merge_hw_tables().merge_files( modules_dep_path,
                                                    modules_pcimap_path,
                                                    pcitable_path )

        if all_modules is None:
            print( "Unable to merge pci id tables." )
            return


        # this is the actual data structure we return
        system_mods= {}

        # these are the lists that will be in system_mods
        network_mods= []
        scsi_mods= []


        # get all the system devices from lspci
        lspci_prog= popen2.Popen3( self.LSPCI_CMD, 1 )
        if lspci_prog is None:
            print( "Unable to run %s with popen2.Popen3" % self.LSPCI_CMD )
            return
        
        returncode= lspci_prog.wait()
        if returncode != 0:
            print( "Running %s failed" % self.LSPCI_CMD )
            return
        else:
            print( "Successfully ran %s" % self.LSPCI_CMD )
            
        for line in lspci_prog.fromchild:
            if string.strip(line) == "":
                continue
    
            parts= string.split(line)

            try:
                classid= self.remove_quotes(parts[2])
                vendorid= self.remove_quotes(parts[3])
                deviceid= self.remove_quotes(parts[4])
            except IndexError:
                print( "Skipping invalid line:", string.strip(line) )
                continue

            if classid not in (self.PCI_CLASS_NETWORK,
                               self.PCI_CLASS_RAID,
                               self.PCI_CLASS_RAID2,
                               self.PCI_CLASS_IDE):
                continue
            
            full_deviceid= "%s:%s" % (vendorid,deviceid)

            for module in all_modules.keys():
                if full_deviceid in all_modules[module]:
                    if classid == self.PCI_CLASS_NETWORK:
                        network_mods.append(module)
                    elif classid in (self.PCI_CLASS_RAID,
                                     self.PCI_CLASS_RAID2,
                                     self.PCI_CLASS_IDE):
                        scsi_mods.append(module)
                        
        system_mods[self.MODULE_CLASS_SCSI]= scsi_mods
        system_mods[self.MODULE_CLASS_NETWORK]= network_mods
        
        return system_mods


    def remove_quotes( self, str ):
        """
        remove double quotes off of a string if they exist
        """
        if str == "" or str == None:
            return str
        if str[:1] == '"':
            str= str[1:]
        if str[len(str)-1] == '"':
            str= str[:len(str)-1]
        return str



if __name__ == "__main__":
    info= systeminfo()
    
    devices= info.get_block_device_list()
    print "block devices detected:"
    if not devices:
        print "no devices found!"
    else:
        for dev in devices.keys():
            print "%s %s" % (dev, repr(devices[dev]))
            

    print ""
    memory= info.get_total_phsyical_mem()
    if not memory:
        print "unable to read /proc/meminfo for memory"
    else:
        print "total physical memory: %d kb" % memory
        

    print ""
    modules= info.get_system_modules("/")
    if not modules:
        print "unable to list system modules"
    else:
        for type in modules:
            if type == info.MODULE_CLASS_SCSI:
                print( "all scsi modules:" )
                for a_mod in modules[type]:
                    print a_mod
            elif type == info.MODULE_CLASS_NETWORK:
                print( "all network modules:" )
                for a_mod in modules[type]:
                    print a_mod
                
