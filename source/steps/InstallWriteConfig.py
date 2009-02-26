#!/usr/bin/python

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.
# expected /proc/partitions format

import os, string

from Exceptions import *
import utils
import systeminfo
import BootAPI
import ModelOptions

def Run( vars, log ):

    """
    Writes out the following configuration files for the node:
    /etc/fstab
    /etc/resolv.conf (if applicable)
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
    INTERFACE_SETTINGS  A dictionary of the values from the network
                                configuration file
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

        INTERFACE_SETTINGS= vars["INTERFACE_SETTINGS"]
        if INTERFACE_SETTINGS == "":
            raise ValueError, "INTERFACE_SETTINGS"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    log.write( "Setting local time to UTC\n" )
    utils.sysexec( "chroot %s ln -sf /usr/share/zoneinfo/UTC /etc/localtime" % \
                   SYSIMG_PATH, log )

    log.write( "Enabling ntp at boot\n" )
    utils.sysexec( "chroot %s chkconfig ntpd on" % SYSIMG_PATH, log )

    log.write( "Creating system directory %s\n" % PLCONF_DIR )
    if not utils.makedirs( "%s/%s" % (SYSIMG_PATH,PLCONF_DIR) ):
        log.write( "Unable to create directory\n" )
        return 0

    log.write( "Writing system /etc/fstab\n" )
    fstab= file( "%s/etc/fstab" % SYSIMG_PATH, "w" )
    fstab.write( "%s           none        swap      sw        0 0\n" % \
                 PARTITIONS["mapper-swap"] )
    fstab.write( "%s           /           ext3      defaults  1 1\n" % \
                 PARTITIONS["mapper-root"] )
    fstab.write( "%s           /vservers   ext3      tagxid,defaults  1 2\n" % \
                 PARTITIONS["mapper-vservers"] )
    fstab.write( "none         /proc       proc      defaults  0 0\n" )
    fstab.write( "none         /dev/shm    tmpfs     defaults  0 0\n" )
    fstab.write( "none         /dev/pts    devpts    defaults  0 0\n" )
    # no longer needed
    # fstab.write( "none         /rcfs       rcfs      defaults  0 0\n" )
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
        method= vars['INTERFACE_SETTINGS']['method']
    except:
        pass
    
    if method == "dhcp":
        utils.sysexec( "cp /etc/resolv.conf %s/etc/" % SYSIMG_PATH, log )

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
