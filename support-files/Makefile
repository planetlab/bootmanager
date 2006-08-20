#
# Build bootstrap tarballs. The alpina-* files are deprecated and are
# only included for historical purposes. Version 2 BootCDs still
# require them; Version 3 BootCDs come with the tools pre-installed.
#
# Aaron Klingaman <alk@absarokasoft.com>
# Mark Huang <mlhuang@cs.princeton.edu>
# Copyright (C) 2005 The Trustees of Princeton University
#
# $Id: Makefile,v 1.3 2005/09/02 20:24:58 mlhuang Exp $
# 

all:	PlanetLab-Bootstrap.tar.bz2

PlanetLab-Bootstrap.tar.bz2:
	./buildnode.sh

clean:
	rm -f PlanetLab-Bootstrap.tar.bz2
