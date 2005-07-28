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


import os, sys, shutil
import popen2
import socket
import fcntl
import string
import exceptions

from Exceptions import *


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



def sysexec( cmd, log= None ):
    """
    execute a system command, output the results to the logger
    if log <> None

    return 1 if command completed (return code of non-zero),
    0 if failed. A BootManagerException is raised if the command
    was unable to execute or was interrupted by the user with Ctrl+C
    """
    prog= popen2.Popen4( cmd, 0 )
    if prog is None:
        raise BootManagerException, \
              "Unable to create instance of popen2.Popen3 " \
              "for command: %s" % cmd

    if log is not None:
        try:
            for line in prog.fromchild:
                log.write( line )
        except KeyboardInterrupt:
            raise BootManagerException, "Interrupted by user"

    returncode= prog.wait()
    if returncode != 0:
        raise BootManagerException, "Running %s failed (rc=%d)" % (cmd,returncode)

    prog= None
    return 1


def sysexec_noerr( cmd, log= None ):
    """
    same as sysexec, but capture boot manager exceptions
    """
    try:
        rc= 0
        rc= sysexec( cmd, log )
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

