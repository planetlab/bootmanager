# 
# $Id: Makefile 682 2007-07-19 09:00:25Z thierry $
#

########## make sync PLCHOST=hostname
########## make sync PLCHOST=hostname
ifdef PLCHOST
ifdef VSERVER
PLCSSH:=root@$(PLCHOST):/vservers/$(VSERVER)
endif
endif

LOCAL_RSYNC_EXCLUDES	:= --exclude '*.pyc' --exclude debug_root_ssh_key
RSYNC_EXCLUDES		:= --exclude .svn --exclude CVS --exclude '*~' --exclude TAGS $(LOCAL_RSYNC_EXCLUDES)
RSYNC_COND_DRY_RUN	:= $(if $(findstring n,$(MAKEFLAGS)),--dry-run,)
RSYNC			:= rsync -a -v $(RSYNC_COND_DRY_RUN) $(RSYNC_EXCLUDES)

sync:
ifeq (,$(PLCSSH))
	echo "sync: You must define PLCHOST and VSERVER on the command line"
	echo " e.g. make sync PLCHOST=private.one-lab.org VSERVER=myplc01" ; exit 1
else
	+$(RSYNC) source $(PLCSSH)/usr/share/bootmanager/
	ssh root@$(PLCHOST) vserver $(VSERVER) exec service plc start bootmanager
endif

##########
tags:
	find . '(' -name '*.py' -o -name '*.spec' ')' | xargs etags

.PHONY: tags
