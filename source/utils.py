#!/usr/bin/python
#
# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.
# expected /proc/partitions format

import os, sys, shutil
import subprocess
import shlex
import socket
import fcntl
import string
import exceptions

from Exceptions import *

####################
# the simplest way to debug is to let the node take off, 
# ssh into it as root using the debug ssh key in /etc/planetlab
# then go to /tmp/source 
# edit this file locally to turn on breakpoints if needed, then run
# ./BootManager.py
####################

### handling breakpoints in the startup process
import select, sys, string

### global debugging settings

# enabling this will cause the node to ask for breakpoint-mode at startup
# production code should read False/False
PROMPT_MODE=False
# default for when prompt is turned off, or it's on but the timeout triggers
BREAKPOINT_MODE=False

# verbose mode is just fine
VERBOSE_MODE=True
# in seconds : if no input, proceed
PROMPT_TIMEOUT=5

def prompt_for_breakpoint_mode ():

    global BREAKPOINT_MODE
    if PROMPT_MODE:
        default_answer=BREAKPOINT_MODE
        answer=''
        if BREAKPOINT_MODE:
            display="[y]/n"
        else:
            display="y/[n]"
        sys.stdout.write ("Want to run in breakpoint mode ? %s "%display)
        sys.stdout.flush()
        r,w,e = select.select ([sys.stdin],[],[],PROMPT_TIMEOUT)
        if r:
            answer = string.strip(sys.stdin.readline())
        else:
            sys.stdout.write("\nTimed-out (%d s)"%PROMPT_TIMEOUT)
        if answer:
            BREAKPOINT_MODE = ( answer == "y" or answer == "Y")
        else:
            BREAKPOINT_MODE = default_answer
    label="Off"
    if BREAKPOINT_MODE:
        label="On"
    sys.stdout.write("\nCurrent BREAKPOINT_MODE is %s\n"%label)

def breakpoint (message, cmd = None):

    if BREAKPOINT_MODE:

        if cmd is None:
            cmd="/bin/sh"
            message=message+" -- Entering bash - type ^D to proceed"

        print message
        os.system(cmd)


########################################
def makedirs( path ):
    """
    from python docs for os.makedirs:
    Throws an error exception if the leaf directory
    already exists or cannot be created.

    That is real useful. Instead, we'll create the directory, then use a
    separate function to test for its existance.

    Return 1 if the directory exists and/or has been created, a BootManagerException
    otherwise. Does not test the writability of said directory.
    """
    try:
        os.makedirs( path )
    except OSError:
        pass
    try:
        os.listdir( path )
    except OSError:
        raise BootManagerException, "Unable to create directory tree: %s" % path
    
    return 1



def removedir( path ):
    """
    remove a directory tree, return 1 if successful, a BootManagerException
    if failure.
    """
    try:
        os.listdir( path )
    except OSError:
        return 1

    try:
        shutil.rmtree( path )
    except OSError, desc:
        raise BootManagerException, "Unable to remove directory tree: %s" % path
    
    return 1


def sysexec( cmd, log=None, fsck=False, shell=False ):
    """
    execute a system command, output the results to the logger
    if log <> None

    return 1 if command completed (return code of non-zero),
    0 if failed. A BootManagerException is raised if the command
    was unable to execute or was interrupted by the user with Ctrl+C
    """
    try:
        # Thierry - Jan. 6 2011
        # would probably make sense to look for | here as well
        # however this is fragile and hard to test thoroughly
        # let the caller set 'shell' when that is desirable
        if shell or cmd.__contains__(">"):
            prog = subprocess.Popen(cmd, shell=True)
            if log is not None:
                log.write("sysexec (shell mode) >>> %s" % cmd)
            if VERBOSE_MODE:
                print "sysexec (shell mode) >>> %s" % cmd
        else:
            prog = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if log is not None:
                log.write("sysexec >>> %s\n" % cmd)
            if VERBOSE_MODE:
                print "sysexec >>> %s" % cmd
    except OSError:
        raise BootManagerException, \
              "Unable to create instance of subprocess.Popen " \
              "for command: %s" % cmd
    try:
        (stdoutdata, stderrdata) = prog.communicate()
    except KeyboardInterrupt:
        raise BootManagerException, "Interrupted by user"

    # log stdout & stderr
    if log is not None:
        if stdoutdata:
            log.write("==========stdout\n"+stdoutdata)
        if stderrdata:
            log.write("==========stderr\n"+stderrdata)

    returncode = prog.wait()

    if fsck:
       # The exit code returned by fsck is the sum of the following conditions:
       #      0    - No errors
       #      1    - File system errors corrected
       #      2    - System should be rebooted
       #      4    - File system errors left uncorrected
       #      8    - Operational error
       #      16   - Usage or syntax error
       #      32   - Fsck canceled by user request
       #      128  - Shared library error
       if returncode != 0 and returncode != 1:
            raise BootManagerException, "Running %s failed (rc=%d)" % (cmd,returncode)
    else:
        if returncode != 0:
            raise BootManagerException, "Running %s failed (rc=%d)" % (cmd,returncode)

    prog = None
    return 1


def sysexec_chroot( path, cmd, log=None, shell=False):
    """
    same as sysexec, but inside a chroot
    """
    preload = ""
    release = os.uname()[2]
    # 2.6.12 kernels need this
    if release[:5] == "2.6.1":
        library = "%s/lib/libc-opendir-hack.so" % path
        if not os.path.exists(library):
            shutil.copy("./libc-opendir-hack.so", library)
        preload = "/bin/env LD_PRELOAD=/lib/libc-opendir-hack.so"
    sysexec("linux32 chroot %s %s %s" % (path, preload, cmd), log, shell=shell)


def sysexec_chroot_noerr( path, cmd, log=None, shell=False ):
    """
    same as sysexec_chroot, but capture boot manager exceptions
    """
    try:
        rc= 0
        rc= sysexec_chroot( cmd, log, shell=shell )
    except BootManagerException, e:
        pass

    return rc


def sysexec_noerr( cmd, log=None, shell=False ):
    """
    same as sysexec, but capture boot manager exceptions
    """
    try:
        rc= 0
        rc= sysexec( cmd, log, shell=shell )
    except BootManagerException, e:
        pass

    return rc



def chdir( dir ):
    """
    change to a directory, return 1 if successful, a BootManagerException if failure
    """
    try:
        os.chdir( dir )
    except OSError:
        raise BootManagerException, "Unable to change to directory: %s" % dir

    return 1



def removefile( filepath ):
    """
    removes a file, return 1 if successful, 0 if failure
    """
    try:
        os.remove( filepath )
    except OSError:
        raise BootManagerException, "Unable to remove file: %s" % filepath

    return 1



# from: http://forums.devshed.com/archive/t-51149/
#              Ethernet-card-address-Through-Python-or-C

def hexy(n):
    return "%02x" % (ord(n))

def get_mac_from_interface(ifname):
    """
    given a device name, like eth0, return its mac_address.
    return None if the device doesn't exist.
    """
    
    SIOCGIFHWADDR = 0x8927 # magic number

    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    ifname = string.strip(ifname)
    ifr = ifname + '\0'*(32-len(ifname))

    try:
        r= fcntl.ioctl(s.fileno(),SIOCGIFHWADDR,ifr)
        addr = map(hexy,r[18:24])
        ret = (':'.join(map(str, addr)))
    except IOError, e:
        ret = None
        
    return ret

def check_file_hash(filename, hash_filename):
    """Check the file's integrity with a given hash."""
    return sha1_file(filename) == open(hash_filename).read().split()[0].strip()

def sha1_file(filename):
    """Calculate sha1 hash of file."""
    try:
        try:
            import hashlib
            m = hashlib.sha1()
        except:
            import sha
            m=sha.new()
        f = file(filename, 'rb')
        while True:
            # 256 KB seems ideal for speed/memory tradeoff
            # It wont get much faster with bigger blocks, but
            # heap peak grows
            block = f.read(256 * 1024)
            if len(block) == 0:
                # end of file
                break
            m.update(block)
            # Simple trick to keep total heap even lower
            # Delete the previous block, so while next one is read
            # we wont have two allocated blocks with same size
            del block
        return m.hexdigest()
    except IOError:
        raise BootManagerException, "Cannot calculate SHA1 hash of %s" % filename
