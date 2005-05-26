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


import os, string

from Exceptions import *
import utils
from systeminfo import systeminfo
import BootAPI


def Run( vars, log ):

    """
    Writes out the following configuration files for the node:
    /etc/fstab
    /etc/hosts
    /etc/sysconfig/network-scripts/ifcfg-eth0
    /etc/resolv.conf (if applicable)
    /etc/sysconfig/network
    /etc/modprobe.conf
    /etc/ssh/ssh_host_key
    /etc/ssh/ssh_host_rsa_key
    /etc/ssh/ssh_host_dsa_key
    
    Expect the following variables from the store:
    VERSION                 the version of the install
    SYSIMG_PATH             the path where the system image will be mounted
                            (always starts with TEMP_PATH)
    PARTITIONS              dictionary of generic part. types (root/swap)
                            and their associated devices.
    PLCONF_DIR              The directory to store the configuration file in
    NETWORK_SETTINGS  A dictionary of the values from the network
                                configuration file
    BOOT_CD_VERSION          A tuple of the current bootcd version
    
    Sets the following variables:
    None
    
    """

    log.write( "\n\nStep: Install: Writing configuration files.\n" )
    
    # make sure we have the variables we need
    try:
        VERSION= vars["VERSION"]
        if VERSION == "":
            raise ValueError, "VERSION"

        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        PARTITIONS= vars["PARTITIONS"]
        if PARTITIONS == None:
            raise ValueError, "PARTITIONS"

        PLCONF_DIR= vars["PLCONF_DIR"]
        if PLCONF_DIR == "":
            raise ValueError, "PLCONF_DIR"

        NETWORK_SETTINGS= vars["NETWORK_SETTINGS"]
        if NETWORK_SETTINGS == "":
            raise ValueError, "NETWORK_SETTINGS"

        BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        if BOOT_CD_VERSION == "":
            raise ValueError, "BOOT_CD_VERSION"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    try:
        # we need to keys in PARTITIONS, root and swap, make sure
        # they exist
        val= PARTITIONS["root"]
        val= PARTITIONS["swap"]
        val= PARTITIONS["vservers"]
        val= PARTITIONS["mapper-root"]
        val= PARTITIONS["mapper-swap"]
        val= PARTITIONS["mapper-vservers"]
    except KeyError, part:
        log.write( "Missing partition in PARTITIONS: %s\n" % part )
        return 0
    

    log.write( "Setting local time to UTC\n" )
    utils.sysexec( "chroot %s ln -sf /usr/share/zoneinfo/UTC /etc/localtime" % \
                   SYSIMG_PATH, log )


    log.write( "Enabling ntp at boot\n" )
    utils.sysexec( "chroot %s chkconfig ntpd on" % SYSIMG_PATH, log )

    log.write( "Creating system directory %s\n" % PLCONF_DIR )
    if not utils.makedirs( "%s/%s" % (SYSIMG_PATH,PLCONF_DIR) ):
        log.write( "Unable to create directory\n" )
        return 0


    log.write( "Writing network configuration\n" )
    write_network_configuration( vars, log )

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
    log.write( "Writing /etc/modprobe.conf\n" )

    sysinfo= systeminfo()
    sysmods= sysinfo.get_system_modules(SYSIMG_PATH)
    if sysmods is None:
        raise BootManagerException, "Unable to get list of system modules."
        
    eth_count= 0
    scsi_count= 0

    modulesconf_file= file("%s/etc/modprobe.conf" % SYSIMG_PATH, "w" )

    for type in sysmods:
        if type == sysinfo.MODULE_CLASS_SCSI:
            for a_mod in sysmods[type]:
                if scsi_count == 0:
                    modulesconf_file.write( "alias scsi_hostadapter %s\n" %
                                            a_mod )
                else:
                    modulesconf_file.write( "alias scsi_hostadapter%d %s\n" %
                                            (scsi_count,a_mod) )
                scsi_count= scsi_count + 1

        elif type == sysinfo.MODULE_CLASS_NETWORK:
            for a_mod in sysmods[type]:
                modulesconf_file.write( "alias eth%d %s\n" %
                                        (eth_count,a_mod) )
                eth_count= eth_count + 1

    modulesconf_file.close()
    modulesconf_file= None


    # dump the modprobe.conf file to the log (not to screen)
    log.write( "Contents of new modprobe.conf file:\n" )
    modulesconf_file= file("%s/etc/modprobe.conf" % SYSIMG_PATH, "r" )
    contents= modulesconf_file.read()
    log.write( contents + "\n" )
    modulesconf_file.close()
    modulesconf_file= None
    log.write( "End contents of new modprobe.conf file.\n" )

    log.write( "Writing system /etc/fstab\n" )
    fstab= file( "%s/etc/fstab" % SYSIMG_PATH, "w" )
    fstab.write( "%s           none        swap      sw        0 0\n" % \
                 PARTITIONS["mapper-swap"] )
    fstab.write( "%s           /           ext3      defaults  0 0\n" % \
                 PARTITIONS["mapper-root"] )
    fstab.write( "%s           /vservers   ext3      tagxid,defaults  0 0\n" % \
                 PARTITIONS["mapper-vservers"] )
    fstab.write( "none         /proc       proc      defaults  0 0\n" )
    fstab.write( "none         /dev/shm    tmpfs     defaults  0 0\n" )
    fstab.write( "none         /dev/pts    devpts    defaults  0 0\n" )
    fstab.write( "none         /rcfs       rcfs      defaults  0 0\n" )
    fstab.close()


    log.write( "Writing system /etc/issue\n" )
    issue= file( "%s/etc/issue" % SYSIMG_PATH, "w" )
    issue.write( "PlanetLab Node: \\n\n" )
    issue.write( "Kernel \\r on an \\m\n" )
    issue.write( "http://www.planet-lab.org\n\n" )
    issue.close()

    log.write( "Setting up authentication (non-ssh)\n" )
    utils.sysexec( "chroot %s authconfig --nostart --kickstart --enablemd5 " \
                   "--enableshadow" % SYSIMG_PATH, log )
    utils.sysexec( "sed -e 's/^root\:\:/root\:*\:/g' " \
                   "%s/etc/shadow > %s/etc/shadow.new" % \
                   (SYSIMG_PATH,SYSIMG_PATH), log )
    utils.sysexec( "chroot %s mv " \
                   "/etc/shadow.new /etc/shadow" % SYSIMG_PATH, log )
    utils.sysexec( "chroot %s chmod 400 /etc/shadow" % SYSIMG_PATH, log )

    # if we are setup with dhcp, copy the current /etc/resolv.conf into
    # the system image so we can run programs inside that need network access
    method= ""
    try:
        method= vars['NETWORK_SETTINGS']['method']
    except:
        pass
    
    if method == "dhcp":
        utils.sysexec( "cp /etc/resolv.conf %s/etc/" % SYSIMG_PATH, log )

    # the kernel rpm should have already done this, so don't fail the
    # install if it fails
    log.write( "Mounting /proc in system image\n" )
    utils.sysexec_noerr( "mount -t proc proc %s/proc" % SYSIMG_PATH, log )

    # mkinitrd references both /etc/modprobe.conf and /etc/fstab
    # as well as /proc/lvm/global. The kernel RPM installation
    # likely created an improper initrd since these files did not
    # yet exist. Re-create the initrd here.
    log.write( "Making initrd\n" )

    # trick mkinitrd in case the current environment does not have device mapper
    fake_root_lvm= 0
    if not os.path.exists( "%s/%s" % (SYSIMG_PATH,PARTITIONS["mapper-root"]) ):
        fake_root_lvm= 1
        utils.makedirs( "%s/dev/mapper" % SYSIMG_PATH )
        rootdev= file( "%s/%s" % (SYSIMG_PATH,PARTITIONS["mapper-root"]), "w" )
        rootdev.close()

    utils.sysexec( "chroot %s sh -c '" \
                   "kernelversion=`ls /lib/modules | tail -1` && " \
                   "rm -f /boot/initrd-$kernelversion.img && " \
                   "mkinitrd /boot/initrd-$kernelversion.img $kernelversion'" % \
                   SYSIMG_PATH, log )

    if fake_root_lvm == 1:
        utils.removefile( "%s/%s" % (SYSIMG_PATH,PARTITIONS["mapper-root"]) )

    log.write( "Writing node install version\n" )
    utils.makedirs( "%s/etc/planetlab" % SYSIMG_PATH )
    ver= file( "%s/etc/planetlab/install_version" % SYSIMG_PATH, "w" )
    ver.write( "%s\n" % VERSION )
    ver.close()

    log.write( "Creating ssh host keys\n" )
    key_gen_prog= "/usr/bin/ssh-keygen"

    log.write( "Generating SSH1 RSA host key:\n" )
    key_file= "/etc/ssh/ssh_host_key"
    utils.sysexec( "chroot %s %s -q -t rsa1 -f %s -C '' -N ''" %
                   (SYSIMG_PATH,key_gen_prog,key_file), log )
    utils.sysexec( "chmod 600 %s/%s" % (SYSIMG_PATH,key_file), log )
    utils.sysexec( "chmod 644 %s/%s.pub" % (SYSIMG_PATH,key_file), log )
    
    log.write( "Generating SSH2 RSA host key:\n" )
    key_file= "/etc/ssh/ssh_host_rsa_key"
    utils.sysexec( "chroot %s %s -q -t rsa -f %s -C '' -N ''" %
                   (SYSIMG_PATH,key_gen_prog,key_file), log )
    utils.sysexec( "chmod 600 %s/%s" % (SYSIMG_PATH,key_file), log )
    utils.sysexec( "chmod 644 %s/%s.pub" % (SYSIMG_PATH,key_file), log )
    
    log.write( "Generating SSH2 DSA host key:\n" )
    key_file= "/etc/ssh/ssh_host_dsa_key"
    utils.sysexec( "chroot %s %s -q -t dsa -f %s -C '' -N ''" %
                   (SYSIMG_PATH,key_gen_prog,key_file), log )
    utils.sysexec( "chmod 600 %s/%s" % (SYSIMG_PATH,key_file), log )
    utils.sysexec( "chmod 644 %s/%s.pub" % (SYSIMG_PATH,key_file), log )

    return 1



def write_network_configuration( vars, log ):
    """
    Write out the network configuration for this machine:
    /etc/hosts
    /etc/sysconfig/network-scripts/ifcfg-eth0
    /etc/resolv.conf (if applicable)
    /etc/sysconfig/network

    It is assumed the caller mounted the root partition and the vserver partition
    starting on SYSIMG_PATH - it is not checked here.

    The values to be used for the network settings are to be set in vars
    in the variable 'NETWORK_SETTINGS', which is a dictionary
    with keys:

     Key               Used by this function
     -----------------------------------------------
     node_id
     node_key
     method            x
     ip                x
     mac               x (optional)
     gateway           x
     network           x
     broadcast         x
     netmask           x
     dns1              x
     dns2              x (optional)
     hostname          x
     domainname        x
    """

    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    try:
        network_settings= vars['NETWORK_SETTINGS']
    except KeyError, e:
        raise BootManagerException, "No network settings found in vars."

    try:
        hostname= network_settings['hostname']
        domainname= network_settings['domainname']
        method= network_settings['method']
        ip= network_settings['ip']
        gateway= network_settings['gateway']
        network= network_settings['network']
        netmask= network_settings['netmask']
        dns1= network_settings['dns1']
    except KeyError, e:
        raise BootManagerException, "Missing value %s in network settings." % str(e)

    try:
        dns2= ''
        dns2= network_settings['dns2']
    except KeyError, e:
        pass

        
    log.write( "Writing /etc/hosts\n" )
    hosts_file= file("%s/etc/hosts" % SYSIMG_PATH, "w" )    
    hosts_file.write( "127.0.0.1       localhost\n" )
    if method == "static":
        hosts_file.write( "%s %s.%s\n" % (ip, hostname, domainname) )
    hosts_file.close()
    hosts_file= None
    

    log.write( "Writing /etc/sysconfig/network-scripts/ifcfg-eth0\n" )
    eth0_file= file("%s/etc/sysconfig/network-scripts/ifcfg-eth0" %
                    SYSIMG_PATH, "w" )
    eth0_file.write( "DEVICE=eth0\n" )
    if method == "static":
        eth0_file.write( "BOOTPROTO=static\n" )
        eth0_file.write( "IPADDR=%s\n" % ip )
        eth0_file.write( "NETMASK=%s\n" % netmask )
        eth0_file.write( "GATEWAY=%s\n" % gateway )
    else:
        eth0_file.write( "BOOTPROTO=dhcp\n" )
        eth0_file.write( "DHCP_HOSTNAME=%s\n" % hostname )
    eth0_file.write( "ONBOOT=yes\n" )
    eth0_file.write( "USERCTL=no\n" )
    eth0_file.close()
    eth0_file= None

    if method == "static":
        log.write( "Writing /etc/resolv.conf\n" )
        resolv_file= file("%s/etc/resolv.conf" % SYSIMG_PATH, "w" )
        if dns1 != "":
            resolv_file.write( "nameserver %s\n" % dns1 )
        if dns2 != "":
            resolv_file.write( "nameserver %s\n" % dns2 )
        resolv_file.write( "search %s\n" % domainname )
        resolv_file.close()
        resolv_file= None

    log.write( "Writing /etc/sysconfig/network\n" )
    network_file= file("%s/etc/sysconfig/network" % SYSIMG_PATH, "w" )
    network_file.write( "NETWORKING=yes\n" )
    network_file.write( "HOSTNAME=%s.%s\n" % (hostname, domainname) )
    if method == "static":
        network_file.write( "GATEWAY=%s\n" % gateway )
    network_file.close()
    network_file= None

