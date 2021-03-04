#!/bin/bash

whorunsit() {
  local l1=`who | awk '{print $1}'`
  if [ ! -z $l1 ]; then
    echo $l1
  else
    l1=`logname`
    echo $l1
  fi
}

TORO2_USER=toro2
TORO2_HOMEDIR=/etc/toro2
TORO2_PATH=/etc
TORO2_CONF=toro2/toro2.conf
TORO2_TOR_DATADIR="$TORO2_HOMEDIR/.tor"
TOR_LIBDIR=/var/lib/tor
TOR_LOGDIR=/var/log/tor
OUT_IFACES_DEFAULT="ppp0"
CHATTR_BIN=
TOR_USER=$(cat /etc/passwd | grep tor | cut -d':' -f1| head -n1)
if [ -z "${TOR_USER}" ]; then TOR_USER=tor; fi

if [ `id -u` -ne 0 ]; then
  echo -e "\n[\e[91m!\e[0m] Root access Required."; exit 1
fi

make_toro2_conf() {
	#define the template.
	echo -e "toro2_homedir=$TORO2_HOMEDIR
toro2_path=$TORO2_PATH
toro2_binary=/usr/bin/toro2
backup_osfiles=False
tor_libdir=$TOR_LIBDIR
tor_logdir=$TOR_LOGDIR
required_services=[ \"privoxy\", \"dnscrypt-proxy\"]
tor_as_process=True
tor_user=$TOR_USER
iptables=$IPTABLES_BIN
iptables_save=$IPTABLES_SAVE_BIN
iptables_restore=$IPTABLES_RESTORE_BIN
ip6tables=$IP6TABLES_BIN
ip6tables_save=$IP6TABLES_SAVE_BIN
ip6tables_restore=$IP6TABLES_RESTORE_BIN
systemctl=$SYSTEMCTL_BIN
username=$TORO2_USER
python3=$PYTHON3_BIN
tor=$TOR_BIN
chattr=$CHATTR_BIN" > $TORO2_CONF
}

myecho() {
	if [ ! -z $VERBOSE ]; then
		echo "$@"
	fi
}

check_service_exists() {
	serviceName="$1"

	if [[ ! -z `systemctl list-unit-files | grep $serviceName` ]]; then return 0;
	else return 1 ; fi
}

OS_MAJOR=
VERBOSE=1
case "$OSTYPE" in
	solaris*) OS_MAJOR="SOLARIS" ;;
	darwin*)  OS_MAJOR="OSX" ;;
	linux*)   OS_MAJOR="LINUX" ;;
	bsd*)     OS_MAJOR="BSD" ;;
	msys*)    OS_MAJOR="WINDOWS" ;;
	*)        echo "unknown: $OSTYPE"; exit 1 ;;
esac

configure_solaris() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER"
}

configure_osx() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER"
}

configure_bsd() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER"
}

configure_windows() {
	echo -e "  \n[\e[93m!\e[0m] Not implemented yet for $OS $VER"
}

which_req_bin() {
	local REQ_BIN_NAME="$1"
	local REQ_BIN=$(which $REQ_BIN_NAME)
	if [[ -z $REQ_BIN ]]; then
		myecho -e "\e[91mNot found!\e[0m : \e[93m$REQ_BIN_NAME\e[0m" ; exit 1;
	else
		myecho -e "[\e[92m!\e[0m] \e[92mFound binary\e[0m : \e[39m$REQ_BIN_NAME\e[0m" ; eval "$(echo $REQ_BIN_NAME | tr '-' '_' | tr '[:lower:]' '[:upper:]')_BIN=$REQ_BIN"
	fi
}

badexit() {
  local msg="$1"
  local code="$2"
  [[ $msg ]] || msg=""
  [[ $code ]] || code=1
  myecho -e $msg ; exit $code
}

configure_linux() {
  local foruser=$(whorunsit)
  [[ $foruser ]] ||	badexit "  \e[91mUser not set!\e[0m" 1

	if [ -f /etc/os-release ]; then
		# freedesktop.org and systemd
		. /etc/os-release
	    	OS=$NAME
	    	VER=$VERSION_ID
	elif type lsb_release >/dev/null 2>&1; then
	    	# linuxbase.org
	    	OS=$(lsb_release -si)
	    	VER=$(lsb_release -sr)
	elif [ -f /etc/lsb-release ]; then
	    	# For some versions of Debian/Ubuntu without lsb_release command
	    	. /etc/lsb-release
	    	OS=$DISTRIB_ID
	    	VER=$DISTRIB_RELEASE
	elif [ -f /etc/debian_version ]; then
	    	# Older Debian/Ubuntu/etc.
	    	OS=Debian
	    	VER=$(cat /etc/debian_version)
	elif [ -f /etc/SuSe-release ]; then
	    	# Older SuSE/etc.
	    	echo "Old Suse. Can't be configured"
		exit 1
	elif [ -f /etc/redhat-release ]; then
	    	# Older Red Hat, CentOS, etc.
	    	echo "Old Red Hat. Can't be configured"
	else
    		# Fall back to uname, e.g. "Linux <version>", also works for BSD, etc.
    		OS=$(uname -s)
    		VER=$(uname -r)
	fi

	myecho -e "OS: $OS\nVersion: $(if [ -z $VER ]; then echo No info; else echo $VER; fi)"

	YUM_CMD=$(which yum 2>/dev/null)
	APT_GET_CMD=$(which apt-get 2>/dev/null)
	PACMAN_CMD=$(which pacman 2>/dev/null)

	if [[ ! -z $APT_GET_CMD ]]; then
    	$APT_GET_CMD update && \
    	$APT_GET_CMD install -y net-tools libevent-dev dnscrypt-proxy privoxy tor proxychains minicom onioncircuits obfs4proxy
	elif [[ ! -z $YUM_CMD ]]; then
		$YUM_CMD -y update && \
		$YUM_CMD -y install net-tools privoxy dnscrypt-proxy tor proxychains onioncircuits obfsproxy obfs4proxy
	elif [[ ! -z $PACMAN_CMD ]]; then
    	$PACMAN_CMD -Su && \
    	$PACMAN_CMD -S netstat-nat dnscrypt-proxy privoxy tor proxychains onioncircuits obfsproxy obfs4proxy
	else
		echo "[\e[92mx\e[0m] No package manager configured for $OS $VER"
		exit 1
	fi

	if [ -z `sudo cat /etc/shadow | grep privoxy` ]; then
    useradd --system --shell /bin/false --no-create-home --group --disabled-login privoxy
	fi

	declare -a required_binaries=("chattr" "python3" "iptables" "iptables-save" "iptables-restore" "ip6tables" "ip6tables-save" "ip6tables-restore" "tor" "systemctl")
	myecho -e "[\e[93m.\e[0m] Configuring ... \n"
	for req_bin in "${required_binaries[@]}"; do
		 which_req_bin $req_bin
	done;

	make_toro2_conf

  sed -i "s~ExecStart=/usr/bin/dnscrypt-proxy~ExecStart=$(which dnscrypt-proxy 2>/dev/null)~g" toro2/usr/lib/systemd/system/dnscrypt-proxy.service
  sed -i "s~ExecStart=/usr/bin/privoxy~ExecStart=$(which privoxy 2>/dev/null)~g" toro2/usr/lib/systemd/system/privoxy.service
  sed -i "s/OUT_IFACES=.*/OUT_IFACES=\"$(netstat -i | awk 'NR >2 {print $1}' | grep -v lo | paste -s -d ' ') $OUT_IFACES_DEFAULT\"/g"  toro2/toro2.iptablesA

  # required services must be 0. stopped 1. disabled by default
  # which gives user an opportunity to run whole toro2 with all servcies
  # only when she explicitly runs it from terminal as 'toro2 start'
  declare -a required_services=("privoxy.service" "dnscrypt-proxy.service" "dnscrypt-proxy.socket" "tor.service")
  myecho -e "[\e[93m.\e[0m] Configuring required services ... \n"
	for req_srv in "${required_services[@]}"; do
    check_service_exists $req_srv
    if [[ $? -eq 1 ]]; then
      myecho -e "  \n[\e[91m!\e[0m] $req_srv \e[91mNOT exists\e[91m but \e[91mREQUIRED\e[0m";
      exit 1;
    fi
    $SYSTEMCTL_BIN stop $req_srv --quiet 2>/dev/null
    $SYSTEMCTL_BIN disable $req_srv --quiet 2>/dev/null
	done;

  # declare -a optional_services=("dnsmasq.service")
  # myecho -e "\n[\e[93m.\e[0m] Configuring optional services ... \n"
	# for opt_srv in "${optional_services[@]}"; do
	#    check_service_exists $opt_srv
  #    if [[ $? -eq 1 ]]; then
  #     myecho -e "  \n[\e[93m!\e[0m] $opt_srv \e[93mNOT exists\e[0m and \e[96mNot strictly Required\e[0m."; fi
  # done

	myecho -e "[\e[92m+\e[0m] Configured Successfully.\n"

  if [ -z $PYTHON3_BIN ]; then
    echo -e "[\e[91m!\e[0m] python3 required\n[\e[91m!\e[0m] Install python3 and restart the installation"; exit 1;
  fi

  $PYTHON3_BIN toro2/toro2.py installnobackup

  declare -a services_to_stop=("avahi-daemon" "avahi-daemon.socket" "systemd-resolved" "cups")
  myecho -e "[\e[93m.\e[0m] Configuring services to be stopped ... \n"
	for srv2stop in "${services_to_stop[@]}"; do
    $SYSTEMCTL_BIN stop $srv2stop --quiet 2>/dev/null
    $SYSTEMCTL_BIN disable $srv2stop --quiet 2>/dev/null
	done;
  $SYSTEMCTL_BIN daemon-reload
  $SYSTEMCTL_BIN reset-failed

  # ----------------------------------------------------------------------------
  # dnscrypt-proxy configure
  # ----------------------------------------------------------------------------
  #local DNSCRYPT_PROXY_USER=$(cat /lib/systemd/system/dnscrypt-proxy.service|grep User|awk -F "=" '{print $2}')
  local DNSCRYPT_PROXY_USER="_dnscrypt-proxy"
  id -u $DNSCRYPT_PROXY_USER 2>/dev/null 1>&2
  if [[ $? -eq 1 ]]; then myecho -e "[\e[91mx\e[0m] No $DNSCRYPT_PROXY_USER user found.\n"; exit 1; fi

  find / -type d -name "dnscrypt-proxy*" 2>/dev/null | grep -v toro2 | xargs chown -R $DNSCRYPT_PROXY_USER:
  find / -type f -name "dnscrypt-proxy*" 2>/dev/null | grep -v toro2 | egrep "\.log|\.toml" | xargs chown $DNSCRYPT_PROXY_USER:

  local dc_srv_filepath=`systemctl show -p FragmentPath dnscrypt-proxy.service|awk  -F'=' '{print $2}'`
  sed -i '/^User.*/s/^#*/#/' $dc_srv_filepath
  sed -i '/^CacheDirectory.*/s/^#*/#/' $dc_srv_filepath
  sed -i "/^LogsDirectory.*/s/^#*/#/" $dc_srv_filepath
  sed -i '/^RuntimeDirectory.*/s/^#*/#/' $dc_srv_filepath
  sed -i '/^Also=dnscrypt-proxy.socket.*/s/^#*/#/' $dc_srv_filepath

  sed -i '/^Requires=dnscrypt-proxy.socket.*/s/^#*/#/' $dc_srv_filepath
  sed -i '/^After=network.target.*/s/^#*/#/' $dc_srv_filepath
  sed -i 's/^Before=.*/Before=nss-lookup.target/' $dc_srv_filepath
  sed -i 's/^Wants=.*/Wants=network-online.target nss-lookup.target/' $dc_srv_filepath

  # while true ; do
  #   read -p "ReCreate /var/cache/dnscrypt-proxy? [Yy/Nn]: " recr_cache_dp
  #   case $recr_cache_dp in
  #      	[yY]* )
  #        	rm -rf /var/cache/private/dnscrypt-proxy
  #        	cd /var/cache && \
  #         mkdir -p private/dnscrypt-proxy && \
  #         ln -s private/dnscrypt-proxy dnscrypt-proxy && \
  #         chown $DNSCRYPT_PROXY_USER: /var/cache/private/dnscrypt-proxy
  #        	break
  #         ;;
  #
  #      	[nN]* ) echo -e "[\e[92m!\e[0m] Directory /var/cache/dnscrypt-proxy will be left as is\n"
  #        	break
  #         ;;
  #
  #      	* ) echo -e "[\e[91m!\e[0m] \e[93mYes\e[0m or \e[93mNo\e[0m answer required\n";
  # 	esac
  # done
  # ----------------------------------------------------------------------------
  # End dnscrypt-proxy configuring
  # ----------------------------------------------------------------------------

  # ----------------------------------------------------------------------------
  # User settings start
  # ----------------------------------------------------------------------------
  myecho -e "[\e[93m.\e[0m] Configuring tor ... \n"
  # TOR_LIBDIR & TORO2_TOR_DATADIR must be owned by TOR_USER
  # if uid != root => own by TORO2_USER
  #    PLUS comment User string in .torrc
  #    PLUS add foruser to TORO2_USER group
  #    PLUS set torrc params DataDirectoryGroupReadable & CacheDirectoryGroupReadable to 1
  # else own by $TOR_USER (as root can run tor as TOR_USER)
  #    PLUS set User root run tor as

  if [[ $foruser != "root" ]]; then
    # add foruser in TORO2_USER group
    usermod -a -G $TORO2_USER $foruser
    chown -R $TORO2_USER: $TOR_LIBDIR
    if [ ! -d $TORO2_TOR_DATADIR ]; then
      mkdir -p $TORO2_TOR_DATADIR
    fi
    chown -R $TORO2_USER: $TORO2_TOR_DATADIR
    sed -i "s/#DataDirectoryGroupReadable.*/DataDirectoryGroupReadable 1/g" $TORO2_HOMEDIR/toro2/toro2.torrc
    sed -i "s/#CacheDirectoryGroupReadable.*/CacheDirectoryGroupReadable 1/g" $TORO2_HOMEDIR/toro2/toro2.torrc

    # Allow TORO2_USER traffic runs through TOR network
    sed -i "s/^TOR_USERNAME=.*/TOR_USERNAME=$TORO2_USER/" $TORO2_HOMEDIR/toro2/toro2.iptablesA
  else
    sed -i "s/#User.*/User ${TOR_USER}/g" $TORO2_HOMEDIR/toro2/toro2.torrc

    sed -i "s/^TOR_USERNAME=.*/TOR_USERNAME=$TOR_USER/" $TORO2_HOMEDIR/toro2/toro2.iptablesA
  fi
  # ----------------------------------------------------------------------------
  # User settings end
  # ----------------------------------------------------------------------------

  myecho -e "[\e[93m.\e[0m] Configuring resolv.conf ... \n"
  if [ -f /etc/resolv.conf ]; then
  	if [[ ! -z `file /etc/resolv.conf | grep "symbolic link"` ]]; then unlink /etc/resolv.conf ; fi
	else
  	chattr -i /etc/resolv.conf && rm -f /etc/resolv.conf ;
  fi

  chattr -i /etc/resolv.conf && \
  echo -e "nameserver ::1\nnameserver 127.0.0.1\noptions edns0 single-request-reopen" > /etc/resolv.conf
  chattr +i /etc/resolv.conf

  echo -e "\n[\e[92m+\e[0m] Done."

}

# configure for root user a little bit differ
configure_$(echo "$OS_MAJOR" | tr '[:upper:]' '[:lower:]') $1
