import string

from Exceptions import *
import utils
import compatibility
from systeminfo import systeminfo
import BootAPI


def Run( vars, log ):
    """
    Load the kernel off of a node and boot to it.
    This step assumes the disks are mounted on SYSIMG_PATH.
    
    Expect the following variables:
    BOOT_CD_VERSION       A tuple of the current bootcd version
    SYSIMG_PATH           the path where the system image will be mounted
                          (always starts with TEMP_PATH)
    ROOT_MOUNTED          the node root file system is mounted

    Sets the following variables:
    ROOT_MOUNTED          the node root file system is mounted
    """

    log.write( "\n\nStep: Chain booting node.\n" )

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
    
    if ROOT_MOUNTED == 0:
        log.write( "Mounting node partitions\n" )

        # old cds need extra utilities to run lvm
        if BOOT_CD_VERSION[0] == 2:
            compatibility.setup_lvm_2x_cd( vars, log )
            
        # simply creating an instance of this class and listing the system
        # block devices will make them show up so vgscan can find the planetlab
        # volume group
        systeminfo().get_block_device_list()
        
        utils.sysexec( "vgscan", log )
        utils.sysexec( "vgchange -ay planetlab", log )

        utils.makedirs( SYSIMG_PATH )

        utils.sysexec( "mount /dev/planetlab/root %s" % SYSIMG_PATH, log )
        utils.sysexec( "mount /dev/planetlab/vservers %s/vservers" %
                       SYSIMG_PATH, log )

        ROOT_MOUNTED= 1
        vars['ROOT_MOUNTED']= 1
        

    node_update_cmd= "/usr/local/planetlab/bin/NodeUpdate.py start noreboot"

    log.write( "Running node update.\n" )
    utils.sysexec( "chroot %s %s" % (SYSIMG_PATH,node_update_cmd), log )

    log.write( "Updating ssh public host key with PLC.\n" )
    ssh_host_key= ""
    try:
        ssh_host_key_file= file("%s/etc/ssh/ssh_host_rsa_key.pub"%SYSIMG_PATH,"r")
        ssh_host_key= ssh_host_key_file.read().strip()
        ssh_host_key_file.close()
        ssh_host_key_file= None
    except IOError, e:
        pass
    
    update_vals= {}
    update_vals['ssh_host_key']= ssh_host_key
    BootAPI.call_api_function( vars, "BootUpdateNode", (update_vals,) )


    log.write( "Copying kernel and initrd for booting.\n" )
    utils.sysexec( "cp %s/boot/kernel-boot /tmp/kernel" % SYSIMG_PATH, log )
    utils.sysexec( "cp %s/boot/initrd-boot /tmp/initrd" % SYSIMG_PATH, log )

    log.write( "Unmounting disks.\n" )
    utils.sysexec_noerr( "chroot %s umount /rcfs" % SYSIMG_PATH, log )
    utils.sysexec_noerr( "umount -r /dev/planetlab/vservers", log )
    utils.sysexec_noerr( "umount -r /dev/planetlab/root", log )
    utils.sysexec_noerr( "vgchange -an", log )

    ROOT_MOUNTED= 0
    vars['ROOT_MOUNTED']= 0

    if BOOT_CD_VERSION[0] == 2:
        log.write( "Unloading modules and chaining booting to new kernel.\n" )
    else:
        log.write( "Chaining booting to new kernel.\n" )

    # further use of log after Upload will only output to screen
    log.Upload()

    # regardless of whether kexec works or not, we need to stop trying to
    # run anything
    cancel_boot_flag= "/tmp/CANCEL_BOOT"
    utils.sysexec( "touch %s" % cancel_boot_flag, log )

    # on 2.x cds (2.4 kernel) for sure, we need to shutdown everything to
    # get kexec to work correctly
    
    utils.sysexec_noerr( "ifconfig eth0 down", log )

    if BOOT_CD_VERSION[0] == 2:
        utils.sysexec_noerr( "killall dhcpcd", log )
    elif BOOT_CD_VERSION[0] == 3:
        utils.sysexec_noerr( "killall dhclient", log )
        
    utils.sysexec_noerr( "umount -a -r -t ext2,ext3", log )
    utils.sysexec_noerr( "modprobe -r lvm-mod", log )
    
    try:
        modules= file("/tmp/loadedmodules","r")
        
        for line in modules:
            module= string.strip(line)
            if module != "":
                utils.sysexec_noerr( "modprobe -r %s" % module, log )
    except IOError:
        log.write( "Couldn't load /tmp/loadedmodules to unload, continuing.\n" )

    try:
        utils.sysexec( "kexec --force --initrd=/tmp/initrd " \
                       "--append=ramdisk_size=8192 /tmp/kernel" )
    except BootManagerException, e:
        # if kexec fails, we've shut the machine down to a point where nothing
        # can run usefully anymore (network down, all modules unloaded, file
        # systems unmounted. write out the error, and cancel the boot process

        log.write( "\n\n" )
        log.write( "-------------------------------------------------------\n" )
        log.write( "kexec failed with the following error. Please report\n" )
        log.write( "this problem to support@planet-lab.org.\n\n" )
        log.write( str(e) + "\n\n" )
        log.write( "The boot process has been canceled.\n" )
        log.write( "-------------------------------------------------------\n\n" )

    return
