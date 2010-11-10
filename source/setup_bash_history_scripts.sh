#!/bin/bash

BASH_PROFILE=/root/.bash_profile
HISTORY_PROFILE=/etc/profile.d/histlog.sh
PERIODIC_SCRIPT=/usr/bin/periodic_upload.sh

cat <<\EOF > $BASH_PROFILE
# NOTE: only upload incremental diffs
if [ -f /tmp/source/configuration ] ; then
    source /tmp/source/configuration
fi
if [ -z "$MONITOR_SERVER" ] ; then
    MONITOR_SERVER=monitor.planet-lab.org
fi
function upload_log ()
{
    file=$1
    path=$2
    base=$( basename $file )
    old=/tmp/${base}.old
    new=/tmp/${base}.new
    log=/tmp/${base}.log
    if [ ! -f $file ] ; then
        return
    fi
    if [ -f $new ] ; then
        cp $new $old
    else
        touch $old
    fi
    cp $file $new
    comm -1 -3 $old $new > $log
    if [ $( stat -c %s $log ) -ne 0 ] ; then
        curl --max-time 60 --silent --insecure https://$MONITOR_SERVER/monitor/uploadlogs --form "dir=$path" --form "log=@$log"
        if [ $? -ne 0 ] ; then
            # the upload has failed, so remove new file so no data is lost
            rm -f /tmp/$( basename $file ).new
        fi
    fi
}

function upload_logs ()
{
    upload_log $1 histfail
}

# NOTE: these aliases aim to upload the history before losing it.
alias reboot="upload_logs /root/.bash_eternal_history ; /sbin/reboot"
alias shutdown="upload_logs /root/.bash_eternal_history ; /sbin/shutdown"
EOF

cat <<\EOF > $HISTORY_PROFILE
export HISTTIMEFORMAT="%s ";
# NOTE: HOSTNAME is not reliably set in failboot or safeboot mode
# NOTE: These steps assign at least a default hostname based on IP
# NOTE: This hostname is used in the bash-prompt-script commands
if [[ -z "$HOSTNAME" || "$HOSTNAME" = "(none)" ]] ; then
    HOSTNAME=`ip addr show dev eth0 | grep inet | tr '/' ' ' | sed -e 's/^ *//g' | cut -f2 -d' '`
fi
if [ -f /etc/sysconfig/network-scripts/ifcfg-eth0 ] ; then
    source /etc/sysconfig/network-scripts/ifcfg-eth0 
    if [ -n "$DHCP_HOSTNAME" ] ; then
        HOSTNAME=$DHCP_HOSTNAME
    else 
        if [ -n "$IPADDR" ] ; then
            HOSTNAME=$IPADDR
        fi
    fi
fi
hostname $HOSTNAME &> /dev/null
if [ -n "$BASH_EXECUTION_STRING" ]; then
    # NOTE: does not work on 2.x versions of bash.
    # NOTE: log commands executed over ssh
    echo "$HOSTNAME $$ ssh:$USER xx `date +%s` $BASH_EXECUTION_STRING" >> /root/.bash_eternal_history;
fi
if [ -e /etc/sysconfig/bash-prompt-xterm ]; then
    PROMPT_COMMAND=/etc/sysconfig/bash-prompt-xterm
fi
EOF
chmod 755 $HISTORY_PROFILE

cat <<\EOF > bash-prompt-script
# NOTE: intended to run after and log every interactive-command 
echo $HOSTNAME $$ $USER "$(history 1)" >> /root/.bash_eternal_history
EOF

for f in bash-prompt-default bash-prompt-xterm ; do
    cp bash-prompt-script /etc/sysconfig/$f
    chmod 755 /etc/sysconfig/$f
done

# NOTE: allow command run directly over ssh to be logged also.
echo "source /etc/profile ; source $BASH_PROFILE" > /root/.bashrc

# NOTE 1: crond is not installed on the boot image, so this maintains a
#         persistent process to upload logs on legacy nodes.
# NOTE 2: A day has 86400 seconds, $RANDOM is between 0-32767
# NOTE 2: So, $RANDOM * 3 is between 0 and 27 hours.
# NOTE 3: The initial delay is randomized in case many nodes reboot at the
#         same time.
initial_delay=$(( $RANDOM * 3 )) 

cat <<EOF > $PERIODIC_SCRIPT
#!/bin/bash
if [ -f $BASH_PROFILE ] ; then
    source $BASH_PROFILE
else
    echo "Cannot source upload_logs() definition!"
    exit 1
fi

# NOTE: exit if anoter process is already running.
if [ \$$ -ne \`pgrep -o periodic\` ] ; then
    # the current PID differs from the oldest periodic_upload pid
    exit 0
fi
sleep $initial_delay
while /bin/true ; do
    upload_logs /root/.bash_eternal_history
    sleep 86400   # sleep for a day
done
EOF

chmod 755 $PERIODIC_SCRIPT
$PERIODIC_SCRIPT < /dev/null > /tmp/upload.log 2>&1 &
