#!/bin/sh

# make sure the yum rpm is in extra-rpms/stage3rpms
if [ ! -e extra-rpms/stage3rpms/yum-*planetlab.noarch.rpm ]; then
    echo "yum RPM doesn't exist in extra-rpms/stage3rpms/"
    echo "see extra-rpms/stage3rpms/README_EXTERNAL_RPMS."
    exit 1
fi

# make sure the pycurl rpm is in extra-rpms/stage3rpms
if [ ! -e extra-rpms/stage3rpms/pycurl-*.i386.rpm ]; then
    echo "pycurl RPM doesn't exist in extra-rpms/stage3rpms/"
    echo "see extra-rpms/stage3rpms/README_EXTERNAL_RPMS."
    exit 1
fi

echo "Adding all extra rpms to extract directory..."
cp -vr extra-rpms/* rpm-extract/

for i in `ls extra-rpms/`; do
    echo $i >> keep-files
done

exit 0

