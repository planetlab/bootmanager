#
# Build bootstrap tarballs. The alpina-* files are deprecated and are
# only included for historical purposes. Version 2 BootCDs still
# require them; Version 3 BootCDs come with the tools pre-installed.
#
# Aaron Klingaman <alk@absarokasoft.com>
# Mark Huang <mlhuang@cs.princeton.edu>
# Copyright (C) 2005 The Trustees of Princeton University
#
# $Id: Makefile,v 1.2 2005/09/02 19:09:33 mlhuang Exp $
# 

all:	alpina-BootLVM.tar.gz alpina-PartDisks.tar.gz PlanetLab-Bootstrap.tar.bz2

alpina-BootLVM.tar.gz:
	./buildsupport.sh build BootLVM

alpina-BootstrapRPM.tar.gz:
	./buildsupport.sh build BootstrapRPM

alpina-PartDisks.tar.gz:
	./buildsupport.sh build PartDisks

PlanetLab-Bootstrap.tar.bz2:
	./buildnode.sh

clean:
	./buildsupport.sh clean
	rm -f PlanetLab-Bootstrap.tar.bz2
