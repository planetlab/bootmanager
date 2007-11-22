# 
# $Id: Makefile 682 2007-07-19 09:00:25Z thierry $
#

########## make sync PLCHOST=hostname
ifdef PLCHOST
PLCSSH:=root@$(PLCHOST)
endif

LOCAL_RSYNC_EXCLUDES	:= --exclude '*.pyc' 
RSYNC_EXCLUDES		:= --exclude .svn --exclude CVS --exclude '*~' --exclude TAGS $(LOCAL_RSYNC_EXCLUDES)
RSYNC_COND_DRY_RUN	:= $(if $(findstring n,$(MAKEFLAGS)),--dry-run,)
RSYNC			:= rsync -a -v $(RSYNC_COND_DRY_RUN) $(RSYNC_EXCLUDES)

sync:
ifeq (,$(PLCSSH))
	echo "sync: You must define target host as PLCHOST on the command line"
	echo " e.g. make sync PLCHOST=private.one-lab.org" ; exit 1
else
	+$(RSYNC) source $(PLCSSH):/plc/root/usr/share/bootmanager/
	ssh $(PLCSSH) chroot /plc/root service plc start bootmanager
endif

##########
tags:
	find . '(' -name '*.py' -o -name '*.spec' ')' | xargs etags
