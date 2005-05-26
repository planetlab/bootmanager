from Exceptions import *

welcome_message= \
"""
********************************************************************************
*                                                                              *
*                             Welcome to PlanetLab                             *
*                             ~~~~~~~~~~~~~~~~~~~~                             *
*                                                                              *
* The PlanetLab boot CD allows you to automatically install this machine as a  *
* node within the PlanetLab overlay network.                                   *
*                                                                              *
* PlanetLab is a global overlay network for developing and accessing new       *
* network services. Our goal is to grow to 1000 geographically distributed     *
* nodes, connected by a diverse collection of links. Toward this end, we are   *
* putting PlanetLab nodes into edge sites, co-location and routing centers,    *
* and homes (i.e., at the end of DSL lines and cable modems). PlanetLab is     *
* designed to support both short-term experiments and long-running services.   *
* Currently running services include network weather maps, network-embedded    *
* storage, peer-to-peer networks, and content distribution networks.           *
*                                                                              *
* Information on joining PlanetLab available at planet-lab.org/consortium/     *
*                                                                              *
********************************************************************************

WARNING : Installing PlanetLab will remove any existing operating system and 
          data from this computer.
"""


def Run( vars, log ):
    """
    Ask the user if we really want to wipe this machine.

    Return 1 if the user accept, 0 if the user denied, and
    a BootManagerException if anything unexpected occurred.
    """

    log.write( "\n\nStep: Confirming install with user.\n" )
    
    try:
        confirmation= ""
        install= 0
        print welcome_message
        
        while confirmation not in ("yes","no"):
            confirmation= \
                raw_input("Are you sure you wish to continue (yes/no):")
        install= confirmation=="yes"
    except EOFError, e:
        pass
    except KeyboardInterrupt, e:
        pass
    
    if install:
        log.write( "\nUser accepted install.\n" )
    else:
        log.write( "\nUser canceled install.\n" )
        
    return install
