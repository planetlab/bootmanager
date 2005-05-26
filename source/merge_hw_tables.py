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



class merge_hw_tables:
    
    def merge_files(self, modules_dep_path, modules_pcimap_path, pcitable_path):
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


        # first step, create an associative array of all the built modules
        for line in modulesdep_file:
            parts= string.split(line,":")
            if len(parts) < 2:
                continue

            full_mod_path= parts[0]
            parts= string.split(full_mod_path,"/")
            module_name= parts[len(parts)-1]
            module_name_len= len(module_name)
            if module_name[module_name_len-3:] == ".ko":
                all_modules[module_name[:-3]]= []


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
                                  "(incorrect format)\n" % line_num )
                continue

            # first two parts are always vendor / device id
            module= line_parts[0]
            vendor_id= line_parts[1]
            device_id= line_parts[2]


            # valid vendor and devices are 10 chars (0xXXXXXXXX) and begin with 0x
            if len(vendor_id) != 10 or len(device_id) != 10:
                sys.stderr.write( "Skipping line %d in pcimap " \
                                  "(invalid vendor/device id length)\n" %
                                  line_num )
                continue
            
            if string.lower(vendor_id[:2]) != "0x" \
                   or string.lower(device_id[:2]) != "0x":
                sys.stderr.write( "Skipping line %d in pcimap " \
                                  "(invalid vendor/device id format)\n" % line_num )
                continue

            # cut down the ids, only need last 4 bytes
            # start at 6 = (10 total chars - 4 last chars need)
            vendor_id= string.lower(vendor_id[6:])
            device_id= string.lower(device_id[6:])
            
            full_id= "%s:%s" % (vendor_id, device_id)
            
            if all_modules.has_key(module):
                if full_id not in all_modules[module]:
                    all_modules[module].append( full_id )
            else:
                # normally shouldn't get here, as the list is
                # prepopulated with all the built modules
                all_modules[module]= [full_id,]


        # parse pcitable, add any more ids for the devices
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
            vendor_id= string.lower(line_parts[0][2:])
            device_id= string.lower(line_parts[1][2:])
            
            full_id= "%s:%s" % (vendor_id, device_id)
            
            # if the first char of the third field is a double
            # quote, the third field is a module, else if the first
            # char of the third field is a 0 (zero), the fifth field is
            # the module name. it would nice if there was any easy way
            # to split a string on spaces, but recognize quoted strings,
            # so they wouldn't be split up. that is the reason for this wierd check
            if line_parts[2][0] == '"':
                module= line_parts[2]
            elif line_parts[2][0] == '0':
                try:
                    module= line_parts[4]
                except ValueError, e:
                    sys.stderr.write( "Skipping line %d in pcitable " \
                                      "(incorrect format 2)\n" % line_num )
                    continue
            else:
                sys.stderr.write( "Skipping line %d in pcitable " \
                                  "(incorrect format 3)\n" % line_num )
                continue

            # remove the first and last char of module (quote marks)
            module= module[1:]
            module= module[:len(module)-1]
            
            # now add it if we don't already have this module -> id mapping
            if all_modules.has_key(module):
                if full_id not in all_modules[module]:
                    all_modules[module].append( full_id )
            else:
                # don't add any modules from pcitable that we don't
                # already know about
                pass

        pcitable_file.close()
        pcimap_file.close()
        modulesdep_file.close()

        return all_modules
    


if __name__ == "__main__":
    def usage():
        print( "\nUsage:" )
        print( "rewrite-pcitable.py <modules.dep> <modules.pcimap> " \
               "<pcitable> [<output>]" )
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


    all_modules= merge_hw_tables().merge_files( sys.argv[1], sys.argv[2],
                                                sys.argv[3] )

    if all_modules is not None:
        for module in all_modules.keys():
            devices= all_modules[module]
            if len(devices) > 0:
                devices_str= string.join( all_modules[module], " " )
                output_file.write( "%s %s\n" % (module,devices_str) )
    else:
        sys.stderr.write( "Unable to list modules.\n" )

    output_file.close()
