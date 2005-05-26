#!/bin/bash

# for each file in support-rpms/*.list, extract the rpm and
# keep the files from the list

# list of stage tar ball we need to build, this is basically
# the list of stage directories
ALL_STAGES='PartDisks BootstrapRPM BootLVM'

# new files, in each stage dir
RPM_EXTRACT_DIR='rpm-extract/'
KEEP_FILE_LIST='keep-files'

# source files, in each stage dir
SOURCE_RPM_DIR='source-rpms/'
EXTRA_FILES='lib-paths'
CUSTOM_SCRIPT='custom.sh'

# destination for upload command
DEST_USER='root'
DEST_SERVER='yankee.cs.princeton.edu'
DEST_PATH='/export0/echo/alpina/'


build()
{
    BUILD_STAGE=$1

    for STAGE_DIR in $BUILD_STAGE; do

        echo "Building $STAGE_DIR"
	cd $STAGE_DIR

        STAGE_DEST_FILE="alpina-$STAGE_DIR.tar.gz"

	for file in `ls $SOURCE_RPM_DIR/*.list`; do
	    RPM_NAME="`basename $file list`rpm"
	    RPM_FILE="$SOURCE_RPM_DIR/$RPM_NAME"
	    
	    echo
	    echo "Extracting $RPM_NAME:"
	    extract $RPM_FILE $RPM_EXTRACT_DIR
	    
	    echo "Files to be kept from $RPM_NAME:"
	    for line in `cat $file`; do
		echo "./$RPM_EXTRACT_DIR/$line"
		echo "./$line" >> $KEEP_FILE_LIST
	    done
   
	done

	if [[ -f $CUSTOM_SCRIPT ]]; then
	    echo "Running stage specific script"
	    ./$CUSTOM_SCRIPT

	    if [[ "$?" -ne 0 ]]; then
		echo "Custom stage script failed, exiting."
		exit 1
	    fi
	fi
   
	echo "Compressing files:"
	cd $RPM_EXTRACT_DIR
	tar --files-from=../$KEEP_FILE_LIST --exclude=CVS -cvzf ../../$STAGE_DEST_FILE
	cd ..

	echo "Completed building $STAGE_DIR"

	cd ..

    done
}

upload()
{
    UPLOAD_STAGE=$1

    STAGE_FILE_LIST=''
    for STAGE_DIR in $UPLOAD_STAGE; do
	STAGE_FILE_LIST="$STAGE_FILE_LIST alpina-$STAGE_DIR.tar.gz"
    done

    scp $STAGE_FILE_LIST $DEST_USER@$DEST_SERVER:$DEST_PATH
}

clean()
{
    CLEAN_STAGE=$1

    for STAGE_DIR in $CLEAN_STAGE; do
	rm -rf $STAGE_DIR/$RPM_EXTRACT_DIR
	rm -f $STAGE_DIR/$KEEP_FILE_LIST

	STAGE_DEST_FILE="alpina-$STAGE_DIR.tar.gz"
	rm -f $STAGE_DEST_FILE

	echo "Cleaned $STAGE_DIR"
    done
}

extract()
{
    RPM=$1
    DEST=$2

    mkdir -p $DEST
    rpm2cpio $RPM > $DEST/out.cpio
    (cd $DEST && cpio -ivd < out.cpio && rm out.cpio)
}

usage()
{
    echo "Usage buildsupport.sh (build|upload|clean)";
}

# find out what do do
COMMAND=$1
STAGE=$2


if [[ -z "$STAGE" ]]; then
    # if the stage is blank, build all
    STAGE=$ALL_STAGES
else
    # make sure the stage exists
    if [[ ! -d "$STAGE" ]]; then
	usage
	exit 1
    fi
fi

case "$COMMAND" in
    build)   build "$STAGE";;
    upload)  upload "$STAGE";;
    clean)   clean "$STAGE";;
    *)       usage; exit 1;;
esac
