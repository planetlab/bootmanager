#!/usr/bin/python
#
# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.


import os

from Exceptions import *
import BootAPI


def Run( vars, log ):
    """
        Stop the RunlevelAgent.py script.  Should proceed
        kexec to reset run_level to 'boot' before kexec
    """

    log.write( "\n\nStep: Stopping RunlevelAgent.py\n" )

    try:
        cmd = "%s/RunlevelAgent.py" % vars['BM_SOURCE_DIR']
        # raise error if script is not present.
        os.stat(cmd)
        os.system("/usr/bin/python %s stop" % cmd)
    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    try:
        update_vals= {}
        update_vals['run_level']='boot'
        BootAPI.call_api_function( vars, "ReportRunlevel", (update_vals,) )
    except BootManagerException, e:
        log.write( "Unable to update boot state for this node at PLC: %s.\n" % e )

    return 1
    

