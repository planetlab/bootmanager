import string

MINHW   = 0x001
SMP     = 0x002
X86_64  = 0x004
INTEL   = 0x008
AMD     = 0x010
NUMA    = 0x020
GEODE   = 0x040
BADHD   = 0x080
LAST    = 0x100

modeloptions = {'smp':SMP,
                'x64':X86_64,
                'i64':X86_64|INTEL,
                'a64':X86_64|AMD,
                'i32':INTEL,
                'a32':AMD,
                'numa':NUMA,
                'geode':GEODE,
                'badhd':BADHD,
                'minhw':MINHW}

def Get(model):
    modelinfo = string.split(model,'/')
    options= 0
    for mi in modelinfo:
        info = string.strip(mi)
        info = info.lower()
        options = options | modeloptions.get(info,0)

    return options
