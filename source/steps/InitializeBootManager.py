#!/usr/bin/python2

# $Id$

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import os
import xmlrpclib
import socket
import string

from Exceptions import *
import utils


# locations of boot os version files
BOOT_VERSION_2X_FILE='/usr/bootme/ID'
BOOT_VERSION_3X_FILE='/pl_version'

# minimium version of the boot os we need to run, as a (major,minor) tuple
MINIMUM_BOOT_VERSION= (3,0)

# minimum version of python required to run the boot manager
MINIMUM_PYTHON_VERSION= (2,2,0)


def Run( vars, log ):
    """
    Setup the boot manager so it can run, do any extra necessary
    hardware setup (to fix old cd problems)

    Sets the following variables:
    PARTITIONS        A dictionary of generic partition types and their
                      associated devices.
    BOOT_CD_VERSION   A two number tuple of the boot cd version
    """

    log.write( "\n\nStep: Initializing the BootManager.\n" )

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

    log.write( "Opening connection to API server\n" )
    try:
        api_inst= xmlrpclib.Server( vars['BOOT_API_SERVER'], verbose=0 )
    except KeyError, e:
        raise BootManagerException, \
              "configuration file does not specify API server URL"

    vars['API_SERVER_INST']= api_inst

    if not __check_boot_version( vars, log ):
        raise BootManagerException, \
              "Boot CD version insufficient to run the Boot Manager"
    else:
        log.write( "Running on boot cd version: %s\n" %
                   str(vars['BOOT_CD_VERSION']) )

    BOOT_CD_VERSION= vars['BOOT_CD_VERSION']
    
    # old cds need extra modules loaded for compaq smart array
    if BOOT_CD_VERSION[0] == 2:

        has_smartarray= utils.sysexec_noerr(
            'lspci | egrep "0e11:b178|0e11:4070|0e11:4080|0e11:4082|0e11:4083"')
        
        if has_smartarray:
            log.write( "Loading support for Compaq smart array\n" )
            utils.sysexec_noerr( "modprobe cciss", log )
            _create_cciss_dev_entries()
            

        has_fusion= utils.sysexec_noerr('lspci | egrep "1000:0030"')
        
        if has_fusion:
            log.write( "Loading support for Fusion MPT SCSI controllers\n" )
            utils.sysexec_noerr( "modprobe mptscsih", log )

# out of the way for rc26
#    log.write( "Loading support for LVM\n" )
#    utils.sysexec_noerr( "modprobe dm_mod", log )
    # for anything that needs to know we are running under the boot cd and
    # not the runtime os
    os.environ['PL_BOOTCD']= "1"
        
    return 1



def __check_boot_version( vars, log ):
    """
    identify which version of the boot os we are running on, and whether
    or not we can run at all on the given version. later, this will be
    used to identify extra packages to download to enable the boot manager
    to run on any supported version.

    2.x cds have the version file in /usr/bootme/ID, which looked like:
    'PlanetLab BootCD v2.0.3'

    3.x cds have the version file in /pl_version, which lookes like:
    'PlanetLab BootCD 3.0-beta0.3'

    All current known version strings that we support:
    PlanetLab BootCD 3.0
    PlanetLab BootCD 3.0-beta0.1
    PlanetLab BootCD 3.0-beta0.3
    PlanetLab BootCD v2.0
    PlanetLab BootCD v2.0.1
    PlanetLab BootCD v2.0.2
    PlanetLab BootCD v2.0.3

    Returns 1 if the boot os version is identified and will work
    to run the boot manager. Two class variables are set:
    BOOT_OS_MAJOR_VERSION
    BOOT_OS_MINOR_VERSION
    version strings with three parts parts to the version ignore the
    middle number (so 2.0.3 is major 2, minor 3)

    Returns 0 if the boot os is insufficient to run the boot manager
    """

    try:
        # check for a 3.x version first
        version_file= file(BOOT_VERSION_3X_FILE,'r')
        full_version= string.strip(version_file.read())
        version_file.close()

        version_parts= string.split(full_version)
        version= version_parts[-1]

        version_numbers= string.split(version,".")
        if len(version_numbers) == 2:
            BOOT_OS_MAJOR_VERSION= int(version_numbers[0])
            BOOT_OS_MINOR_VERSION= int(version_numbers[1])
        else:
            # for 3.x cds, if there are more than two parts
            # separated by a ., its one of the beta cds.
            # hardcode as a 3.0 cd
            BOOT_OS_MAJOR_VERSION= 3
            BOOT_OS_MINOR_VERSION= 0

        vars['BOOT_CD_VERSION']= (BOOT_OS_MAJOR_VERSION,BOOT_OS_MINOR_VERSION)
        
        if (BOOT_OS_MAJOR_VERSION,BOOT_OS_MINOR_VERSION) >= \
               MINIMUM_BOOT_VERSION:
            return 1

    except IOError, e:
        pass
    except IndexError, e:
        pass
    except TypeError, e:
        pass


    try:
        # check for a 2.x version first
        version_file= file(BOOT_VERSION_2X_FILE,'r')
        full_version= string.strip(version_file.read())
        version_file.close()

        version_parts= string.split(full_version)
        version= version_parts[-1]
        if version[0] == 'v':
            version= version[1:]

        version_numbers= string.split(version,".")
        if len(version_numbers) == 2:
            BOOT_OS_MAJOR_VERSION= int(version_numbers[0])
            BOOT_OS_MINOR_VERSION= int(version_numbers[1])
        else:
            BOOT_OS_MAJOR_VERSION= int(version_numbers[0])
            BOOT_OS_MINOR_VERSION= int(version_numbers[2])

        vars['BOOT_CD_VERSION']= (BOOT_OS_MAJOR_VERSION,BOOT_OS_MINOR_VERSION)

        if (BOOT_OS_MAJOR_VERSION,BOOT_OS_MINOR_VERSION) >= \
           MINIMUM_BOOT_VERSION:
            return 1

    except IOError, e:
        pass
    except IndexError, e:
        pass
    except TypeError, e:
        pass


    return 0



def _create_cciss_dev_entries():
    def mkccissnod(dev,node):
        dev = dev + " b 104 %d" % (node)
	cmd = "mknod /dev/cciss/%s" %dev
        utils.sysexec_noerr(cmd)
        node = node + 1
        return node

    node = 0
    for i in range(0,16):
        dev = "c0d%d" % i
        node = mkccissnod(dev,node)
        for j in range(1,16):
            subdev = dev + "p%d" % j
            node = mkccissnod(subdev,node)
