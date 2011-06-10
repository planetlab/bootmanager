#!/usr/bin/python
#
# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

from Exceptions import *
import BootAPI
import notify_messages
import os.path


def Run( vars, log ):
    """
        UpdateLastBootOnce will update the last_* values for the node only
        once per boot.  This helps calculate last_time_spent_online and
        last_time_spent_offline for collecting run-time metrics.
    """

    log.write( "\n\nStep: Updating node last boot times at PLC.\n" )

    update_vals= {}
    try:
        if not os.path.isfile("/tmp/UPDATE_LAST_BOOT_ONCE"):
            BootAPI.call_api_function( vars, "BootUpdateNode", (update_vals,) )
            log.write( "Successfully updated boot state for this node at PLC\n" )
            os.system("touch /tmp/UPDATE_LAST_BOOT_ONCE")
    except BootManagerException, e:
        log.write( "Unable to update last boot times for this node at PLC: %s.\n" % e )

    return 1
