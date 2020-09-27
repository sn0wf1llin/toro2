#!/bin/bash

TORO2_USER=toro2
TORO2_HOMEDIR=/etc/toro2
if [ -d $TORO2_HOMEDIR ]; then mkdir $TORO2_HOMEDIR ; fi
TORO2_PATH=/etc
TORO2_CONF="$TORO2_HOMEDIR/toro2/toro2.conf"
TORO2_DATADIR="$TORO2_HOMEDIR/.tor"
TOR_LIBDIR=/var/lib/tor
TOR_LOGDIR=/var/log/tor

if [ `id -u` -ne 0 ]; then
  echo -e "\n[\e[91m!\e[0m] Root access Required."; exit 1
fi

function make_toro2_conf() {
	#define the template.
	echo -e "toro2_homedir=$TORO2_HOMEDIR
toro2_path=$TORO2_PATH
toro2_binary=/usr/bin/toro2
backup_osfiles=False
tor_libdir=$TOR_LIBDIR
tor_logdir=$TOR_LOGDIR
required_services=[\"dnscrypt-proxy\", \"privoxy\"]
tor_as_process=True
iptables=$IPTABLES_BIN
iptables_save=$IPTABLES_SAVE_BIN
iptables_restore=$IPTABLES_RESTORE_BIN
ip6tables=$IP6TABLES_BIN
ip6tables_save=$IP6TABLES_SAVE_BIN
ip6tables_restore=$IP6TABLES_RESTORE_BIN
systemctl=$SYSTEMCTL_BIN
username=toro2
python3=$PYTHON3_BIN
tor=$TOR_BIN" > $TORO2_CONF
}

function myecho() {
	if [ ! -z $VERBOSE ]; then
		echo "$@"
	fi
}

function check_service_exists() {
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

function configure_solaris() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER"
}

function configure_osx() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER"
}

function configure_bsd() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER"
}

function configure_windows() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER"
}

function which_req_bin() {
	local REQ_BIN_NAME="$1"
	local REQ_BIN=$(which $REQ_BIN_NAME)
	if [[ -z $REQ_BIN ]]; then myecho -e "\t\e[91mNot found!\e[0m : \e[93m$REQ_BIN_NAME\e[0m" ; exit 1;
else myecho -e "  [\e[92m!\e[0m] \e[92mFound binary\e[0m : \e[39m$REQ_BIN_NAME\e[0m" ; eval "$(echo $REQ_BIN_NAME | tr '-' '_' | tr '[:lower:]' '[:upper:]')_BIN=$REQ_BIN"
	fi
}

function configure_linux() {
  foruser="$1"

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
    	$APT_GET_CMD update && $APT_GET_CMD install -y libevent-dev dnscrypt-proxy privoxy tor proxychains minicom
	elif [[ ! -z $YUM_CMD ]]; then
		$YUM_CMD -y update && \
		$YUM_CMD -y install privoxy dnscrypt-proxy tor proxychains
	elif [[ ! -z $PACMAN_CMD ]]; then
    	$PACMAN_CMD -Su && $PACMAN_CMD -S dnscrypt-proxy privoxy tor proxychains
	else
		echo "No package manager configured for $OS $VER"
		exit 1
	fi

	if [ -z `sudo cat /etc/shadow | grep privoxy` ]; then
		useradd --system --shell /bin/false --no-create-home --group --disabled-login privoxy
	fi

	declare -a required_binaries=("python3" "iptables" "iptables-save" "iptables-restore" "ip6tables" "ip6tables-save" "ip6tables-restore" "tor" "systemctl")
	myecho -e "\nConfiguring ... \n"
	for req_bin in "${required_binaries[@]}"; do
		 which_req_bin $req_bin
	done;

	check_service_exists "privoxy.service" ; if [[ $? -eq 1 ]]; then myecho -e "\n[\e[91m!\e[0m] privoxy.service \e[91mNOT exists\e[91m but \e[91mREQUIRED\e[0m"; exit 1; fi
	check_service_exists "dnscrypt-proxy.service" ; if [[ $? -eq 1 ]]; then myecho -e "[\e[91m!\e[0m] dnscrypt-proxy.service \e[91mNOT exists\e[0m but \e[91mREQUIRED\e[0m"; exit 1; fi
	check_service_exists "dnsmasq.service" ; if [[ $? -eq 1 ]]; then myecho -e "[\e[93m!\e[0m] dnsmasq.service \e[93mNOT exists\e[0m and \e[96mNot strictly Required\e[0m. You can install it to use dnsmasq later"; fi

	make_toro2_conf

	echo -e "\n[\e[92m+\e[0m] Configured Successfully."

  if [ -z $PYTHON3_BIN ]; then echo -e "[\e[91m!\e[0m] python3 required\n[\e[91m!\e[0m] Install python3 and restart the installation"; exit 1; fi
  $PYTHON3_BIN toro2/toro2.py installnobackup

  if [ $foruser != "root" ]; then
    if [ ! -d $TORO2_DATADIR ]; then mkdir -p $TORO2_DATADIR; fi
    chmod -R $TORO2_USER: $TORO2_DATADIR
    sed -i 's/DataDirectory.*/DataDirectory "$TORO2_DATADIR"/g' $TORO2_HOMEDIR/toro2/toro2.torrc
  else sed -i 's/#User/User/g' $TORO2_HOMEDIR/toro2/toro2.torrc
  fi

}

# configure for root user a little bit differ
configure_$(echo "$OS_MAJOR" | tr '[:upper:]' '[:lower:]') $1
