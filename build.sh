#!/bin/bash

rm -f *.fo *.pdf pdn-titlepage.xsl

#xsltproc -output pdn-titlepage.xsl \
#    /usr/share/sgml/docbook/xsl-stylesheets/template/titlepage.xsl \
#    pdn-titlepage.xml

xmlto -x pdn-pdf-style.xsl pdf boot-manager-pdn.xml
