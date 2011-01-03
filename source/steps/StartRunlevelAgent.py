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
        Start the RunlevelAgent.py script.  Should follow
        AuthenticateWithPLC() in order to guarantee that
        /etc/planetlab/session is present.
    """

    log.write( "\n\nStep: Starting RunlevelAgent.py\n" )

    try:
        cmd = "%s/monitor-runlevelagent" % vars['BM_SOURCE_DIR']
        # raise error if script is not present.
        os.stat(cmd)
        # init script only starts RLA once.
        os.system("/bin/sh %s start bootmanager" % cmd)
    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    return 1
    

