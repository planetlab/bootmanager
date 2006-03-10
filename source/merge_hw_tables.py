#!/usr/bin/env python

"""
The point of this small utility is to take a file in the format
of /lib/modules/`uname -r`/modules.pcimap and /usr/share/hwdata/pcitable
and output a condensed, more easily used format for module detection. This is
done by first getting a list of all the built modules, then loading the
pci ids for each of those modules from modules.pcimap, then finally merging
in the contents of pcitable (for built modules only). The result should be
a file with a pretty comprehensive mapping of pci ids to module names.

The output is used by the PlanetLab boot cd (3.0+) and the pl_hwinit script
to load all the applicable modules by scanning lspci output.



Expected format of file modules.dep includes lines of:

/full/module/path/mod.ko: <dependencies>

Expected format of file modules.pcimap includes lines of:

# pci_module vendor device subvendor subdevice class class_mask driver_data
cciss 0x00000e11 0x0000b060 0x00000e11 0x00004070 0x00000000 0x00000000 0x0
cciss 0x00000e11 0x0000b178 0x00000e11 0x00004070 0x00000000 0x00000000 0x0

Expected format of file pcitable includes lines of:

# ("%d\t%d\t%s\t"%s"\n", vendid, devid, moduleName, cardDescription)
# or ("%d\t%d\t%d\t%d\t%s\t"%s"\n", vendid, devid, subvendid, subdevid, moduleNa
# me, cardDescription)
0x0e11  0x0508  "tmspci"        "Compaq|Netelligent 4/16 Token Ring"
0x1000  0x0407  0x8086  0x0532  "megaraid"      "Storage RAID Controller SRCU42X"

Lines listing a module name of ignore or unknown from pcitable are skipped



Output format, for each line that matches the above lines:
cciss 0e11:b060 0e11:b178

"""

import os, sys
import string

PCI_ANY = 0xffffffffL

def merge_files(modules_dep_path, modules_pcimap_path, pcitable_path):
    """
    merge the three files as described above, and return a dictionary.
    keys are module names, value is a list of pci ids for that module,
    in the form "0e11:b178"
    """

    try:
        modulesdep_file= file(modules_dep_path,"r")
    except IOError:
        sys.stderr.write( "Unable to open modules.dep: %s\n" %
                          modules_dep_path )
        return

    try:
        pcimap_file= file(modules_pcimap_path,"r")
    except IOError:
        sys.stderr.write( "Unable to open modules.pcimap: %s\n" %
                          modules_pcimap_path )
        return

    try:
        pcitable_file= file(pcitable_path,"r")
    except IOError:
        sys.stderr.write( "Unable to open pcitable: %s\n" %
                          pcitable_path )
        return

    # associative array to store all matches of module -> ['vendor:device',..]
    # entries
    all_modules= {}
    all_pci_ids= {}

    # first step, create an associative array of all the built modules
    for line in modulesdep_file:
        parts= string.split(line,":")
        if len(parts) < 2:
            continue

        full_mod_path= parts[0]
        parts= string.split(full_mod_path,"/")
        module= parts[len(parts)-1]
        module_len= len(module)
        if module[module_len-3:] == ".ko":
            module= module[:-3]
            all_modules[module]= []

    modulesdep_file.close()

    # now, parse the pcimap and add devices
    line_num= 0
    for line in pcimap_file:
        line_num= line_num+1

        # skip blank lines, or lines that begin with # (comments)
        line= string.strip(line)
        if len(line) == 0:
            continue

        if line[0] == "#":
            continue

        line_parts= string.split(line)
        if line_parts is None or len(line_parts) != 8:
            sys.stderr.write( "Skipping line %d in pcimap " \
                              "(incorrect format %s)\n" % (line_num,line) )
            continue

        # first two parts are always vendor / device id
        module= line_parts[0]

        try:
            vendor_id= long(line_parts[1],16)
        except ValueError, e:
            sys.stderr.write( "Skipping line %d in %s " \
                              "(incorrect vendor id format %s)\n" % (line_num,modules_pcimap_path,line_parts[1]))
            continue

        try:
            device_id= long(line_parts[2],16)
        except ValueError, e:
            sys.stderr.write( "Skipping line %d in %s " \
                              "(incorrect device id format %s)\n" % (line_num,modules_pcimap_path,line_parts[2]))
            continue

        try:
            subvendor_id= long(line_parts[3],16)
        except ValueError, e:
            sys.stderr.write( "Skipping line %d in %s " \
                              "(incorrect subvendor id format %s)\n" % (line_num,modules_pcimap_path,line_parts[3]))
            continue

        try:
            subdevice_id= long(line_parts[4],16)
        except ValueError, e:
            sys.stderr.write( "Skipping line %d in %s " \
                              "(incorrect subdevice id format %s)\n" % (line_num,modules_pcimap_path,line_parts[4]))
            continue

        full_id= (vendor_id, device_id, subvendor_id, subdevice_id)
        if not all_modules.has_key(module):
            # normally shouldn't get here, as the list is
            # prepopulated with all the built modules

            # XXX we probably shouldn't be doing this at all
            all_modules[module] = [full_id]
        else:
            all_modules[module].append(full_id)
            
        if all_pci_ids.has_key(full_id):
            # conflict as there are multiple modules that support
            # particular pci device
            all_pci_ids[full_id].append(module)
        else:
            all_pci_ids[full_id]= [module]

    pcimap_file.close()

    # parse pcitable, add any more ids for the devices
    # We make the (potentially risky) assumption that pcitable contains
    # only unique (vendor,device,subvendor,subdevice) entries.
    line_num= 0
    for line in pcitable_file:
        line_num= line_num+1

        # skip blank lines, or lines that begin with # (comments)
        line= string.strip(line)
        if len(line) == 0:
            continue

        if line[0] == "#":
            continue

        line_parts= string.split(line)
        if line_parts is None or len(line_parts) <= 2:
            sys.stderr.write( "Skipping line %d in pcitable " \
                              "(incorrect format 1)\n" % line_num )
            continue

        # vendor id is always the first field, device the second. also,
        # strip off first two chars (the 0x)
        try:
            vendor_id= long(line_parts[0],16)
        except ValueError, e:
            sys.stderr.write( "Skipping vendor_id %s in %s on line %d\n" \
                              % (line_parts[0],pcitable_path,line_num))
            continue

        try:
            device_id= long(line_parts[1],16)
        except ValueError, e:
            sys.stderr.write( "Skipping device %s in %s on line %d\n" \
                              % (line_parts[1],pcitable_path,line_num))
            continue

        # if the first char of the third field is a double
        # quote, the third field is a module, else if the first
        # char of the third field is a 0 (zero), the fifth field is
        # the module name. it would nice if there was any easy way
        # to split a string on spaces, but recognize quoted strings,
        # so they wouldn't be split up. that is the reason for this wierd check
        if line_parts[2][0] == '"':
            module= line_parts[2]

            subvendor_id=PCI_ANY
            subdevice_id=PCI_ANY
        elif line_parts[2][0] == '0':
            try:
                module= line_parts[4]
            except ValueError, e:
                sys.stderr.write( "Skipping line %d in pcitable " \
                                  "(incorrect format 2)\n" % line_num )
                continue
            try:
                subvendor_id= long(line_parts[2],16)
            except ValueError, e:
                sys.stderr.write( "Skipping line %d in pcitable " \
                                  "(incorrect format 2a)\n" % line_num )
                continue
            
            try:
                subdevice_id= long(line_parts[3],16)
            except ValueError, e:
                sys.stderr.write( "Skipping line %d in pcitable " \
                                  "(incorrect format 2b)\n" % line_num )

        else:
            sys.stderr.write( "Skipping line %d in pcitable " \
                              "(incorrect format 3)\n" % line_num )
            continue

        # remove the first and last char of module (quote marks)
        module= module[1:]
        module= module[:len(module)-1]

        full_id= (vendor_id, device_id, subvendor_id, subdevice_id)

        if not all_modules.has_key(module):
            # Do not process any modules listed in pcitable for which
            # we do not have a prebuilt module.
            continue

        if not full_id in all_modules[module]:
            all_modules[module].append(full_id)

        if all_pci_ids.has_key(full_id):
            if not module in all_pci_ids[full_id]:
                all_pci_ids[full_id].append(module)
            
            # check if there are duplicate mappings between modules
            # and full_ids
            if len(all_pci_ids[full_id])>1:
                # collect the set of modules that are different than what
                # is listed in the pcitables file
                other_modules = []
                for other_module in all_pci_ids[full_id]:
                    if other_module != module:
                        other_modules.append(other_module)

                # remove full_id from the set of other modules in all_modules {}
                for other_module in other_modules:
                    all_modules[other_module].remove(full_id)

                # ensure that there is only one full_id -> module 
                all_pci_ids[full_id] = [module]

        else:
            all_pci_ids[full_id] = [module]
                
    pcitable_file.close()

    return (all_pci_ids,all_modules)

if __name__ == "__main__":
    def usage():
        print( "\nUsage:" )
        print( "%s <modules.dep> <modules.pcimap> " \
               "<pcitable> [<output>]" % sys.argv[0] )
        print( "" )
        
    if len(sys.argv) < 4:
        usage()
        sys.exit(1)


    if len(sys.argv) > 4:
        output_file_name= sys.argv[4]
        try:
            output_file= file(output_file_name,"w")
        except IOError:
            sys.stderr.write( "Unable to open %s for writing.\n" % output_file )
            sys.exit(1)
    else:
        output_file= sys.stdout


    (all_pci_ids,all_modules)=merge_files( sys.argv[1],
                                           sys.argv[2],
                                           sys.argv[3] )
    if all_modules is not None:
        for module in all_modules.keys():
            pci_ids = all_modules[module]
            if len(pci_ids)>0:
                output_file.write("%s" % module)
                for pci_id in pci_ids:
                    output_file.write(" %x:%x:%x:%x" % pci_id)
                output_file.write(" \n")
    else:
        sys.stderr.write( "Unable to list modules.\n" )

    output_file.close()
