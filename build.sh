#!/bin/bash

# build a bash script that can be executed by the boot cd,
# and contains embedded in it the boot manager.

DEST_SCRIPT=bootmanager.sh

cat > $DEST_SCRIPT << '_EOF_'
#!/bin/bash
set -e

UUDECODE=/usr/bin/uudecode

# once we get the beta cds out of use, this can be removed
if [ ! -x $UUDECODE ]; then
  UUDECODE=/tmp/uudecode
  curl -s http://boot.planet-lab.org/boot/uudecode.gz | gzip -d -c > $UUDECODE
  chmod +x $UUDECODE
fi

_EOF_
echo '($UUDECODE | /bin/tar -C /tmp -xj) << _EOF_' >> $DEST_SCRIPT
tar -cj source/ | uuencode -m - >> $DEST_SCRIPT
echo '_EOF_' >> $DEST_SCRIPT
echo 'cd /tmp/source' >> $DEST_SCRIPT
echo 'chmod +x BootManager.py && ./BootManager.py' >> $DEST_SCRIPT
