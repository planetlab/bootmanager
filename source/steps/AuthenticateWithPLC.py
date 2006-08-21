#!/usr/bin/python2

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.


import os

from Exceptions import *
import BootAPI


AUTH_FAILURE_COUNT_FILE= "/tmp/authfailurecount"


def Run( vars, log ):
    """
    Authenticate this node with PLC. This ensures that the node can operate
    as normal, and that our management authority has authorized it.

    For this, just call the PLC api function BootCheckAuthentication

    Return 1 if authorized, a BootManagerException if not or the
    call fails entirely.

    If there are two consecutive authentication failures, put the node
    into debug mode and exit the bootmanager.

    Expect the following variables from the store:
    NUM_AUTH_FAILURES_BEFORE_DEBUG    How many failures before debug
    """

    log.write( "\n\nStep: Authenticating node with PLC.\n" )

    # make sure we have the variables we need
    try:
        NUM_AUTH_FAILURES_BEFORE_DEBUG= int(vars["NUM_AUTH_FAILURES_BEFORE_DEBUG"])
    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    try:
        authorized= BootAPI.call_api_function( vars, "BootCheckAuthentication", () )
        if authorized == 1:
            log.write( "Authentication successful.\n" )

            try:
                os.unlink( AUTH_FAILURE_COUNT_FILE )
            except OSError, e:
                pass
            
            return 1
    except BootManagerException, e:
        log.write( "Authentication failed: %s.\n" % e )

    # increment auth failure
    auth_failure_count= 0
    try:
        auth_failure_count= int(file(AUTH_FAILURE_COUNT_FILE,"r").read().strip())
    except IOError:
        pass
    except ValueError:
        pass

    auth_failure_count += 1

    try:
        fail_file= file(AUTH_FAILURE_COUNT_FILE,"w")
        fail_file.write( str(auth_failure_count) )
        fail_file.close()
    except IOError:
        pass

    if auth_failure_count >= NUM_AUTH_FAILURES_BEFORE_DEBUG:
        log.write( "Maximum number of authentication failures reached.\n" )
        log.write( "Canceling boot process and going into debug mode.\n" )

    raise BootManagerException, "Unable to authenticate node."
    

