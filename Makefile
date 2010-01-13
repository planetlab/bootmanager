# 
# $Id: Makefile 682 2007-07-19 09:00:25Z thierry $
#

########## sync
# 2 forms are supported
# (*) if your plc root context has direct ssh access:
# make sync PLC=private.one-lab.org
# (*) otherwise, entering through the root context
# make sync PLCHOST=testbox1.inria.fr GUEST=vplc03.inria.fr

ifdef GUEST
ifdef PLCHOST
SSHURL:=root@$(PLCHOST):/vservers/$(GUEST)
SSHCOMMAND:=ssh root@$(PLCHOST) vserver $(GUEST)
endif
endif
ifdef PLC
SSHURL:=root@$(PLC):/
SSHCOMMAND:=ssh root@$(PLC)
endif

LOCAL_RSYNC_EXCLUDES	:= --exclude '*.pyc' 
RSYNC_EXCLUDES		:= --exclude .svn --exclude CVS --exclude '*~' --exclude TAGS $(LOCAL_RSYNC_EXCLUDES)
RSYNC_COND_DRY_RUN	:= $(if $(findstring n,$(MAKEFLAGS)),--dry-run,)
RSYNC			:= rsync -a -v $(RSYNC_COND_DRY_RUN) $(RSYNC_EXCLUDES)

DEPLOYMENT ?= regular

sync:
ifeq (,$(SSHURL))
	@echo "sync: You must define, either PLC, or PLCHOST & GUEST, on the command line"
	@echo " you can optionnally define DEPLOYMENT too, it defaults to 'regular'"
	@echo "  e.g. make sync PLC=boot.onelab.eu DEPLOYMENT=alpha"
	@echo "  or   make sync PLCHOST=testbox1.inria.fr GUEST=vplc03.inria.fr"
	@exit 1
else
	$(SSHCOMMAND) mkdir -p /usr/share/bootmanager/$(DEPLOYMENT)
	+$(RSYNC) build.sh source $(SSHURL)/usr/share/bootmanager/$(DEPLOYMENT)
	$(SSHCOMMAND) service plc start bootmanager
endif

##########
tags:
	find . '(' -name '*.py' -o -name '*.spec' ')' | xargs etags

.PHONY: tags
