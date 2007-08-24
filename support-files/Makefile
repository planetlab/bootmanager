#
# Build bootstrap tarballs. The alpina-* files are deprecated and are
# only included for historical purposes. Version 2 BootCDs still
# require them; Version 3 BootCDs come with the tools pre-installed.
#
# Aaron Klingaman <alk@absarokasoft.com>
# Mark Huang <mlhuang@cs.princeton.edu>
# Copyright (C) 2005 The Trustees of Princeton University
#
# $Id: Makefile,v 1.5 2007/03/08 17:52:21 mef Exp $
# 

all:	PlanetLab-Bootstrap.tar.bz2

PlanetLab-Bootstrap.tar.bz2:
 	./buildnode.sh -r $$([ -f "/etc/fedora-release" ] && awk ' { if ($3=="Core") print $4; else print $3 } ' /etc/fedora-release || echo 4)

clean:
	rm -f PlanetLab-Bootstrap.tar.bz2
