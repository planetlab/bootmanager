<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<xsl:import href="http://docbook.sourceforge.net/release/xsl/current/fo/docbook.xsl"/>

<xsl:param name="section.autolabel" select="1"></xsl:param>

<xsl:param name="table.frame.border.thickness" select="'0.5pt'"></xsl:param>
<xsl:param name="nominal.table.width" select="'6in'"></xsl:param>

<xsl:param name="header.rule" select="0"></xsl:param>
<xsl:param name="footer.rule" select="0"></xsl:param>


<!-- remove table of contents -->
<xsl:param name="generate.toc">
article nop
</xsl:param>

<!-- remove revision history -->
<xsl:template match="revhistory" mode="titlepage.mode">
</xsl:template>

<!-- remove normal header -->
<xsl:template match="header.content">
</xsl:template>

</xsl:stylesheet>
