import os

from Exceptions import *
import utils
from systeminfo import systeminfo
import compatibility


def Run( vars, log ):
    """
    See if a node installation is valid. More checks should certainly be
    done in the future, but for now, make sure that the sym links kernel-boot
    and initrd-boot exist in /boot
    
    Expect the following variables to be set:
    SYSIMG_PATH              the path where the system image will be mounted
                             (always starts with TEMP_PATH)
    BOOT_CD_VERSION          A tuple of the current bootcd version
    ROOT_MOUNTED             the node root file system is mounted
    
    Set the following variables upon successfully running:
    ROOT_MOUNTED             the node root file system is mounted
    """

    log.write( "\n\nStep: Validating node installation.\n" )

    # make sure we have the variables we need
    try:
        BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        if BOOT_CD_VERSION == "":
            raise ValueError, "BOOT_CD_VERSION"

        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    ROOT_MOUNTED= 0
    if 'ROOT_MOUNTED' in vars.keys():
        ROOT_MOUNTED= vars['ROOT_MOUNTED']

    # old cds need extra utilities to run lvm
    if BOOT_CD_VERSION[0] == 2:
        compatibility.setup_lvm_2x_cd( vars, log )
        
    # simply creating an instance of this class and listing the system
    # block devices will make them show up so vgscan can find the planetlab
    # volume group
    systeminfo().get_block_device_list()

    # mount the root system image if we haven't already.
    # capture BootManagerExceptions during the vgscan/change and mount
    # calls, so we can return 0 instead
    if ROOT_MOUNTED == 0:
        try:
            utils.sysexec( "vgscan", log )
            utils.sysexec( "vgchange -ay planetlab", log )
        except BootManagerException, e:
            log.write( "BootManagerException during vgscan/vgchange: %s\n" %
                       str(e) )
            return 0
            
        utils.makedirs( SYSIMG_PATH )

        try:
            utils.sysexec( "mount /dev/planetlab/root %s" % SYSIMG_PATH, log )
            utils.sysexec( "mount /dev/planetlab/vservers %s/vservers" %
                           SYSIMG_PATH, log )
        except BootManagerException, e:
            log.write( "BootManagerException during vgscan/vgchange: %s\n" %
                       str(e) )
            return 0

        ROOT_MOUNTED= 1
        vars['ROOT_MOUNTED']= 1
        
    valid= 0
    
    if os.access("%s/boot/kernel-boot" % SYSIMG_PATH, os.F_OK | os.R_OK) and \
           os.access("%s/boot/initrd-boot" % SYSIMG_PATH, os.F_OK | os.R_OK):
        valid= 1

    if not valid:
        log.write( "Node does not appear to be installed correctly:\n" )
        log.write( "missing file /boot/ initrd-boot or kernel-boot\n" )
        return 0
    
    return 1
