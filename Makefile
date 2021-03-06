#

########## sync
# 2 forms are supported
# (*) if your plc root context has direct ssh access:
# make sync PLC=private.one-lab.org
# (*) otherwise, entering through the root context
# make sync PLCHOST=testbox1.inria.fr GUEST=vplc03.inria.fr

PLCHOST ?= testplc.onelab.eu

ifdef GUEST
SSHURL:=root@$(PLCHOST):/vservers/$(GUEST)
SSHCOMMAND:=ssh root@$(PLCHOST) vserver $(GUEST) exec
endif
ifdef PLC
SSHURL:=root@$(PLC):/
SSHCOMMAND:=ssh root@$(PLC)
endif

LOCAL_RSYNC_EXCLUDES	:= --exclude '*.pyc' 
RSYNC_EXCLUDES		:= --exclude .svn --exclude .git --exclude '*~' --exclude TAGS $(LOCAL_RSYNC_EXCLUDES)
RSYNC_COND_DRY_RUN	:= $(if $(findstring n,$(MAKEFLAGS)),--dry-run,)
RSYNC			:= rsync -a -v $(RSYNC_COND_DRY_RUN) $(RSYNC_EXCLUDES)

DEPLOYMENT ?= regular

sync:
ifeq (,$(SSHURL))
	@echo "sync: You must define, either PLC, or PLCHOST & GUEST, on the command line"
	@echo "  e.g. make sync PLC=boot.planetlab.eu"
	@echo "  or   make sync PLCHOST=testplc.onelab.eu GUEST=vplc03.inria.fr"
	@exit 1
else
	$(SSHCOMMAND) mkdir -p /usr/share/bootmanager/$(DEPLOYMENT)
	+$(RSYNC) build.sh source $(SSHURL)/usr/share/bootmanager/$(DEPLOYMENT)
	$(SSHCOMMAND) service plc start bootmanager
endif

##########
tags:
	find . -type f | egrep -v 'TAGS|/\.svn/|\.git/|~$$' | xargs etags

.PHONY: tags
