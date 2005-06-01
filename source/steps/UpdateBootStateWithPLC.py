from Exceptions import *
import BootAPI
import notify_messages


def Run( vars, log ):
    """
    Change this nodes boot state at PLC.

    The current value of the BOOT_STATE key in vars is used.
    Optionally, notify the contacts of the boot state change.
    If this is the case, the following keys/values
    should be set in vars before calling this step:
    STATE_CHANGE_NOTIFY= 1
    STATE_CHANGE_NOTIFY_MESSAGE= "<notify message>"
    The second value is a message to send the users from notify_messages.py

    Return 1 if succesfull, a BootManagerException otherwise.
    """

    log.write( "\n\nStep: Updating node boot state at PLC.\n" )

    update_vals= {}
    update_vals['boot_state']= vars['BOOT_STATE']
    BootAPI.call_api_function( vars, "BootUpdateNode", (update_vals,) )

    log.write( "Successfully updated boot state for this node at PLC\n" )


    if "STATE_CHANGE_NOTIFY" in vars.keys():
        if vars["STATE_CHANGE_NOTIFY"] == 1:
            message= vars['STATE_CHANGE_NOTIFY_MESSAGE']
            include_pis= 0
            include_techs= 1
            include_support= 0
            
            sent= 0
            try:
                sent= BootAPI.call_api_function( vars, "BootNotifyOwners",
                                                 (message,
                                                  include_pis,
                                                  include_techs,
                                                  include_support) )
            except BootManagerException, e:
                log.write( "Call to BootNotifyOwners failed: %s.\n" % e )
                
            if sent == 0:
                log.write( "Unable to notify site contacts of state change.\n" )
    
    return 1