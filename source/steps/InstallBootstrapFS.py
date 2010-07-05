#!/usr/bin/python
#
# $Id$
# $URL$
#
# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2007 The Trustees of Princeton University
# All rights reserved.
# expected /proc/partitions format

import os, sys, string
import popen2
import shutil
import traceback 

from Exceptions import *
import utils
import BootServerRequest
import BootAPI


def Run( vars, log ):
    """
    Download core + extensions bootstrapfs tarballs and install on the hard drive
    
    Expect the following variables from the store:
    SYSIMG_PATH          the path where the system image will be mounted
    PARTITIONS           dictionary of generic part. types (root/swap)
                         and their associated devices.
    NODE_ID              the id of this machine
    
    Sets the following variables:
    TEMP_BOOTCD_PATH     where the boot cd is remounted in the temp
                         path
    ROOT_MOUNTED         set to 1 when the the base logical volumes
                         are mounted.
    """

    log.write( "\n\nStep: Install: bootstrapfs tarball.\n" )

    # make sure we have the variables we need
    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        PARTITIONS= vars["PARTITIONS"]
        if PARTITIONS == None:
            raise ValueError, "PARTITIONS"

        NODE_ID= vars["NODE_ID"]
        if NODE_ID == "":
            raise ValueError, "NODE_ID"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    try:
        # make sure the required partitions exist
        val= PARTITIONS["root"]
        val= PARTITIONS["swap"]
        val= PARTITIONS["vservers"]
    except KeyError, part:
        log.write( "Missing partition in PARTITIONS: %s\n" % part )
        return 0   

    bs_request= BootServerRequest.BootServerRequest(vars)
    
    log.write( "turning on swap space\n" )
    utils.sysexec( "swapon %s" % PARTITIONS["swap"], log )

    # make sure the sysimg dir is present
    utils.makedirs( SYSIMG_PATH )

    log.write( "mounting root file system\n" )
    utils.sysexec( "mount -t ext3 %s %s" % (PARTITIONS["root"],SYSIMG_PATH), log )

    log.write( "mounting vserver partition in root file system\n" )
    utils.makedirs( SYSIMG_PATH + "/vservers" )
    utils.sysexec( "mount -t ext3 %s %s/vservers" % (PARTITIONS["vservers"],
                                                     SYSIMG_PATH), log )

    vars['ROOT_MOUNTED']= 1

    # call getNodeFlavour
    try:
        node_flavour = BootAPI.call_api_function(vars, "GetNodeFlavour", (NODE_ID,) )
        nodefamily = node_flavour['nodefamily']
        extensions = node_flavour['extensions']
        plain = node_flavour['plain']
    except:
        raise BootManagerException ("Could not call GetNodeFlavour - need PLCAPI-5.0")
    
    # the 'plain' option is for tests mostly
    if plain:
        download_suffix=".tar"
        uncompress_option=""
        log.write("Using plain bootstrapfs images\n")
    else:
        download_suffix=".tar.bz2"
        uncompress_option="-j"
        log.write("Using compressed bootstrapfs images\n")

    log.write ("Using nodefamily=%s\n"%(nodefamily))
    if not extensions:
        log.write("Installing only core software\n")
    else:
        log.write("Requested extensions %r" % extensions)
    
    bootstrapfs_names = [ nodefamily ] + extensions

    for name in bootstrapfs_names:
        tarball = "bootstrapfs-%s%s"%(name,download_suffix)
        source_file= "/boot/%s" % (tarball)
        dest_file= "%s/%s" % (SYSIMG_PATH, tarball)

        source_hash_file= "/boot/%s.sha1sum" % (tarball)
        dest_hash_file= "%s/%s.sha1sum" % (SYSIMG_PATH, tarball)

        # 30 is the connect timeout, 14400 is the max transfer time in
        # seconds (4 hours)
        log.write( "downloading %s\n" % source_file )
        result = bs_request.DownloadFile( source_file, None, None,
                                         1, 1, dest_file,
                                         30, 14400)

        if result:
            # Download SHA1 checksum file
            result = bs_request.DownloadFile( source_hash_file, None, None,
                                         1, 1, dest_hash_file,
                                         30, 14400)
 
            if not utils.check_file_hash(dest_file, dest_hash_file):
                raise BootManagerException, "FATAL: SHA1 checksum does not match between %s and %s" % (source_file, source_hash_file)
                
            log.write( "extracting %s in %s\n" % (dest_file,SYSIMG_PATH) )
            result = utils.sysexec( "tar -C %s -xpf %s %s" % (SYSIMG_PATH,dest_file,uncompress_option), log )
            log.write( "Done\n")
            utils.removefile( dest_file )
        else:
            # the main tarball is required
            if name == nodefamily:
                raise BootManagerException, "FATAL: Unable to download main tarball %s from server." % \
                    source_file
            # for extensions, just print a warning
            else:
                log.write("WARNING: tarball for extension %s not found\n"%(name))

    # copy resolv.conf from the base system into our temp dir
    # so DNS lookups work correctly while we are chrooted
    log.write( "Copying resolv.conf to temp dir\n" )
    utils.sysexec( "cp /etc/resolv.conf %s/etc/" % SYSIMG_PATH, log )

    # Copy the boot server certificate(s) and GPG public key to
    # /usr/boot in the temp dir.
    log.write( "Copying boot server certificates and public key\n" )

    if os.path.exists("/usr/boot"):
        utils.makedirs(SYSIMG_PATH + "/usr")
        shutil.copytree("/usr/boot", SYSIMG_PATH + "/usr/boot")
    elif os.path.exists("/usr/bootme"):
        utils.makedirs(SYSIMG_PATH + "/usr/boot")
        boot_server = file("/usr/bootme/BOOTSERVER").readline().strip()
        shutil.copy("/usr/bootme/cacert/" + boot_server + "/cacert.pem",
                    SYSIMG_PATH + "/usr/boot/cacert.pem")
        file(SYSIMG_PATH + "/usr/boot/boot_server", "w").write(boot_server)
        shutil.copy("/usr/bootme/pubring.gpg", SYSIMG_PATH + "/usr/boot/pubring.gpg")
        
    # For backward compatibility
    if os.path.exists("/usr/bootme"):
        utils.makedirs(SYSIMG_PATH + "/mnt/cdrom")
        shutil.copytree("/usr/bootme", SYSIMG_PATH + "/mnt/cdrom/bootme")

    # Import the GPG key into the RPM database so that RPMS can be verified
    utils.makedirs(SYSIMG_PATH + "/etc/pki/rpm-gpg")
    utils.sysexec("gpg --homedir=/root --export --armor" \
                  " --no-default-keyring --keyring %s/usr/boot/pubring.gpg" \
                  " >%s/etc/pki/rpm-gpg/RPM-GPG-KEY-planetlab" % (SYSIMG_PATH, SYSIMG_PATH))
    utils.sysexec_chroot(SYSIMG_PATH, "rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-planetlab")

    return 1
