#!/bin/bash

whorunsit() {
  local l1=`who | awk '{print $1}'` ;
  if [[ ! -z ${l1} ]]; then
    echo ${l1} ;
  else
    l1=`logname` ;
    echo ${l1} ;
  fi ;
}

TORO2_CONF="toro2/toro2.conf" ;
OUT_IFACES_DEFAULT="ppp0" ;

if [[ `id -u` -ne 0 ]]; then
  echo -e "\n[\e[91m!\e[0m] Root access Required.";
  exit 1 ;
fi

readconf() {
  local vararray="$1" ;
  local key value ;
  local IFS="=" ;
  declare -g -A "$vararray" ;
  while read; do
    [[ $REPLY == [^#]*[^$IFS]${IFS}[^$IFS]* ]] && {
      read key value <<< "$REPLY"
      [[ -n $key ]] || continue
      eval "$vararray[$key]=\"\$value\""
    }
  done ;
}

readconf myconf < $TORO2_CONF ;
# echo ${myconf["tor_trans_port"]}

mk_conf() {
    TOR_LIBDIR=${myconf['tor_libdir']} ;
    TOR_LOGDIR=${myconf['tor_logdir']} ;
    TORO2_HOMEDIR=${myconf['toro2_homedir']} ;
    TORO2_PATH=${myconf['toro2_path']} ;
    TORO2_USER=${myconf['username']} ;
    DNSCRYPT_PROXY_USER=${myconf['dnscrypt_proxy_user']} ;
    TOR_USER=${myconf['tor_user']} ;

    if [[ -z $TOR_USER ]]; then
        TOR_USER=$(cat /etc/passwd | grep tor | cut -d':' -f1| head -n1) ;
        if [[ -z "${TOR_USER}" ]]; then TOR_USER=tor; fi ;
    fi ;

	# sed -i "s!toro2_homedir=.*!toro2_homedir=$TORO2_HOMEDIR!" $TORO2_CONF ;
	# sed -i "s!toro2_path=.*!toro2_path=$TORO2_PATH!" $TORO2_CONF ;
	# sed -i "s!tor_libdir=.*!tor_libdir=$TOR_LIBDIR!" $TORO2_CONF ;
	# sed -i "s!tor_logdir=.*!tor_logdir=$TOR_LOGDIR!" $TORO2_CONF ;

    sed -i "s/tor_user=.*/tor_user=$TOR_USER/" $TORO2_CONF ;
	sed -i "s!iptables=.*!iptables=$IPTABLES_BIN!" $TORO2_CONF ;
	sed -i "s!iptables_save=.*!iptables_save=$IPTABLES_SAVE_BIN!" $TORO2_CONF ;
	sed -i "s!iptables_restore=.*!iptables_restore=$IPTABLES_RESTORE_BIN!" $TORO2_CONF ;
	sed -i "s!ip6tables=.*!ip6tables=$IP6TABLES_BIN!" $TORO2_CONF ;
	sed -i "s!ip6tables_save=.*!ip6tables_save=$IP6TABLES_SAVE_BIN!" $TORO2_CONF ;
	sed -i "s!ip6tables_restore=.*!ip6tables_restore=$IP6TABLES_RESTORE_BIN!" $TORO2_CONF ;
	sed -i "s!systemctl=.*!systemctl=$SYSTEMCTL_BIN!" $TORO2_CONF ;
	sed -i "s/username=.*/username=$TORO2_USER/" $TORO2_CONF ;
	sed -i "s!python3=.*!python3=$PYTHON3_BIN!" $TORO2_CONF ;
	# sed -i "s!tor=.*!tor=$TOR_BIN!" $TORO2_CONF ;
	sed -i "s!chattr=.*!chattr=$CHATTR_BIN!" $TORO2_CONF ;

}

myecho() {
	if [[ ! -z $VERBOSE ]]; then
		echo "$@" ;
	fi ;
}

check_service_exists() {
	serviceName="$1" ;

	if [[ ! -z `systemctl list-unit-files | grep $serviceName` ]]; then return 0;
	else return 1 ; fi ;
}

OS_MAJOR= ;
VERBOSE=1 ;
case "$OSTYPE" in
	solaris*) OS_MAJOR="SOLARIS" ;;
	darwin*)  OS_MAJOR="OSX" ;;
	linux*)   OS_MAJOR="LINUX" ;;
	bsd*)     OS_MAJOR="BSD" ;;
	msys*)    OS_MAJOR="WINDOWS" ;;
	*)        echo "unknown: $OSTYPE"; exit 1 ;;
esac

configure_solaris() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER" ;
}

configure_osx() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER" ;
}

configure_bsd() {
	echo -e "\n[\e[93m!\e[0m] Not implemented yet for $OS $VER" ;
}

configure_windows() {
	echo -e "  \n[\e[93m!\e[0m] Not implemented yet for $OS $VER" ;
}

which_req_bin() {
	local REQ_BIN_NAME="$1" ;
	local REQ_BIN=$(which $REQ_BIN_NAME) ;
	if [[ -z $REQ_BIN ]]; then
		myecho -e "\e[91mNot found!\e[0m : \e[93m$REQ_BIN_NAME\e[0m" ;
		exit 1;
	else
		myecho -e "[\e[92m!\e[0m] \e[92mFound binary\e[0m : \e[39m$REQ_BIN_NAME\e[0m ($REQ_BIN)" ;
		eval "$(echo $REQ_BIN_NAME | tr '-' '_' | tr '[:lower:]' '[:upper:]')_BIN=$REQ_BIN" ;
	fi ;
}

badexit() {
  local msg="$1" ;
  local code="$2" ;
  [[ ${msg} ]] || msg="" ;
  [[ ${code} ]] || code=1 ;
  myecho -e ${msg} ;
  exit ${code} ;
}

configure_linux() {
  local foruser=$(whorunsit) ;

  #[[ $foruser ]] ||	badexit "  \e[91mUser not set!\e[0m" 1 ;

	if [[ -e /etc/os-release ]]; then
		# freedesktop.org and systemd
		    . /etc/os-release ;
	    	OS=$NAME ;
	    	VER=$VERSION_ID ;
	elif type lsb_release >/dev/null 2>&1; then
	    	# linuxbase.org
	    	OS=$(lsb_release -si) ;
	    	VER=$(lsb_release -sr) ;
	elif [[ -f /etc/lsb-release ]]; then
	    	# For some versions of Debian/Ubuntu without lsb_release command
	    	. /etc/lsb-release ;
	    	OS=$DISTRIB_ID ;
	    	VER=$DISTRIB_RELEASE ;
	elif [[ -f /etc/debian_version ]]; then
	    	# Older Debian/Ubuntu/etc.
	    	OS=Debian ;
	    	VER=$(cat /etc/debian_version) ;
	elif [[ -f /etc/SuSe-release ]]; then
	    	# Older SuSE/etc.
	    	echo "Old Suse. Can't be configured" ;
		    exit 1 ;
	elif [[ -f /etc/redhat-release ]]; then
	    	# Older Red Hat, CentOS, etc.
	    	echo "Old Red Hat. Can't be configured" ;
            exit 1 ;
	else
    		# Fall back to uname, e.g. "Linux <version>", also works for BSD, etc.
    		OS=$(uname -s) ; VER=$(uname -r) ;
	fi ;

	myecho -e "OS: $OS\nVersion: $(if [[ -z $VER ]]; then echo No info; else echo $VER; fi)" ;

	YUM_PKGMGR=$(which yum 2>/dev/null) ;
	APT_GET_PKGMGR=$(which apt-get 2>/dev/null) ;
	PACMAN_PKGMGR=$(which pacman 2>/dev/null) ;

	if [[ ! -z $APT_GET_PKGMGR ]]; then
        $APT_GET_PKGMGR update && $APT_GET_PKGMGR install -y git net-tools libevent-dev python3-pip \
            dnscrypt-proxy privoxy tor proxychains minicom \
            onioncircuits obfs4proxy tor openvpn unzip;
	elif [[ ! -z $YUM_PKGMGR ]]; then
		$YUM_PKGMGR -y update && $YUM_PKGMGR -y install git net-tools privoxy dnscrypt-proxy python3-pip \
            tor proxychains onioncircuits obfsproxy obfs4proxy tor openvpn unzip;
	elif [[ ! -z $PACMAN_PKGMGR ]]; then
        $PACMAN_PKGMGR -Sy && $PACMAN_PKGMGR -Su && $PACMAN_PKGMGR -S git netstat-nat dnscrypt-proxy privoxy \
            tor proxychains tor openvpn unzip;
	else
		echo "[\e[92mx\e[0m] No package manager configured for $OS $VER" ;
		exit 1 ;
	fi ;

  id privoxy 2>/dev/null 1>&2;
  if [[ $? -ne 0 ]]; then
    useradd --system --shell /bin/false --no-create-home --group --disabled-login privoxy ;
  fi ;

  declare -a required_binaries=("chattr" "python3" "iptables" "iptables-save" "iptables-restore" "ip6tables" "ip6tables-save" "ip6tables-restore" "tor" "systemctl" "dnscrypt-proxy") ;
  myecho -e "[\e[93m.\e[0m] Configuring ... \n" ;
  for req_bin in "${required_binaries[@]}"; do
		 which_req_bin $req_bin ;
  done;

  mk_conf ;

  [[ -z $PYTHON3_BIN ]] && echo -e "[\e[91m!\e[0m] python3 required\n[\e[91m!\e[0m] Install python3 and restart the installation" && exit 1 ;

  ln -sf $PYTHON3_BIN `which python` ;
  $PYTHON3_BIN toro2/toro2.py installnobackup ;

  chmod 755 $TORO2_HOMEDIR/toro2/toro2.py $TORO2_HOMEDIR/toro2/toro2.torrc ;
  chmod 644 $TORO2_HOMEDIR/toro2/toro2.conf ;
  # sed -i "s~ExecStart=/usr/bin/dnscrypt-proxy~ExecStart=$(which dnscrypt-proxy 2>/dev/null) --config ~g" /usr/lib/systemd/system/dnscrypt-proxy.service ;
  # sed -i "s~ExecStart=/usr/bin/privoxy~ExecStart=$(which privoxy 2>/dev/null)~g" toro2/usr/lib/systemd/system/privoxy.service ;
  sed -i "s/OUT_IFACES=.*/OUT_IFACES=\"$(netstat -i | awk 'NR >2 {print $1}' | grep -v lo | paste -s -d ' ') $OUT_IFACES_DEFAULT\"/"  $TORO2_HOMEDIR/toro2/toro2.iptablesA ;

  # toro2 dns port setup
  local dns_port=$(cat toro2/toro2.conf |grep -i "dnscrypt_proxy_port"|awk -F '=' '{print $2}') ;
  sed -i "s/DNS_PORT=.*/DNS_PORT=$dns_port/" $TORO2_HOMEDIR/toro2/toro2.iptablesA ;
  sed -i "s/port=.*/port=$dns_port/" $TORO2_HOMEDIR/toro2/etc/dnsmasq.conf ;

  # sysctl net.ipv4.ip_forward=1
  # sysctl net.ipv6.ip_forward=1

  # toro2 tor trans port setup
  local trans_port=$(cat toro2/toro2.conf |grep -i "tor_trans_port"|awk -F '=' '{print $2}') ;
  sed -i "s/TRANS_PORT=.*/TRANS_PORT=$trans_port/" $TORO2_HOMEDIR/toro2/toro2.iptablesA ;
  sed -i "s/TransPort.*/TransPort $trans_port/" $TORO2_HOMEDIR/toro2/toro2.torrc ;

  # required services must be 0. stopped 1. disabled by default
  # which gives user an opportunity to run whole toro2 with all services
  # only when she explicitly runs it from terminal as 'toro2 start'
  declare -a required_services=("privoxy.service" "dnscrypt-proxy.service" "tor.service")   ;
  myecho -e "[\e[93m.\e[0m] Stop & disable required services from autostart when no TorO2 used... \n" ;
  for req_srv in "${required_services[@]}"; do
    check_service_exists $req_srv  ;
    if [[ $? -eq 1 ]]; then
        myecho -e "  \n[\e[91m!\e[0m] $req_srv \e[91mNOT exists\e[91m but \e[91mREQUIRED\e[0m" ;
        exit 1;
    fi ;

    $SYSTEMCTL_BIN stop $req_srv --quiet 2>/dev/null ;
    $SYSTEMCTL_BIN disable $req_srv --quiet 2>/dev/null ;

  done;

  declare -a optional_services=("dnsmasq.service") ;
  myecho -e "\n[\e[93m.\e[0m] Configuring optional services ... \n" ;
  for opt_srv in "${optional_services[@]}"; do
    check_service_exists $opt_srv ;
    if [[ $? -eq 1 ]]; then
      myecho -e "  \n[\e[93m!\e[0m] $opt_srv \e[93mNOT exists\e[0m and \e[96mNot strictly Required\e[0m.";
    fi ;
  done ;

  myecho -e "[\e[92m+\e[0m] success.\n" ;

  sed -i "s/listen_addresses.*/listen_addresses = ['127.0.0.1:$dns_port', '[::1]:$dns_port']/" /etc/dnscrypt-proxy/dnscrypt-proxy.toml ;
  sed -i "s!http_proxy.*!http_proxy = 'http://127.0.0.1:8118'!" /etc/dnscrypt-proxy/dnscrypt-proxy.toml ;
  sed -i "s!force_tcp.*!force_tcp = true!" /etc/dnscrypt-proxy/dnscrypt-proxy.toml  ;

  declare -a services_to_stop=("avahi-daemon" "avahi-daemon.socket" "systemd-resolved" "cups") ;
  myecho -e "[\e[93m.\e[0m] Configuring services to be stopped & disabled ... \n" ;
  for srv2stop in "${services_to_stop[@]}"; do
    $SYSTEMCTL_BIN stop $srv2stop --quiet 2>/dev/null ;
    $SYSTEMCTL_BIN disable $srv2stop --quiet 2>/dev/null ;
  done;

  # ----------------------------------------------------------------------------
  # dnscrypt-proxy configure step 0
  # ----------------------------------------------------------------------------

  local dc_srv_filepath=`$SYSTEMCTL_BIN show -p FragmentPath dnscrypt-proxy.service|awk  -F'=' '{print $2}'` ;

  sed -i 's/^After=.*/After=nss-lookup.target/' $dc_srv_filepath ;
  sed -i "s/^User.*/User=$TORO2_USER/" $dc_srv_filepath ;
  sed -i '/^Also=dnscrypt-proxy.socket.*/s/^#*/#/' $dc_srv_filepath ;
  sed -i '/^Requires=dnscrypt-proxy.socket.*/s/^#*/#/' $dc_srv_filepath ;
  sed -i '/^Before=.*/s/^#*/#/' $dc_srv_filepath ;
  sed -i 's/^Wants=.*/Wants=network-online.target/' $dc_srv_filepath ;

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
  # dnscrypt-proxy configure step 1
  # ----------------------------------------------------------------------------
  myecho -e "[\e[93m.\e[0m] dnscrypt-proxy step 1\n" ;
  [[ -d /var/cache/private/dnscrypt-proxy ]] && rm -rf /var/cache/private/dnscrypt-proxy ;
  [[ -L /var/cache/dnscrypt-proxy ]] && unlink /var/cache/dnscrypt-proxy ;
  [[ -d /var/cache/dnscrypt-proxy ]] && rm -rf /var/cache/dnscrypt-proxy ;
  [[ -d /var/log/dnscrypt-proxy ]] && rm -rf /var/log/dnscrypt-proxy ;

  mkdir -p /var/cache/dnscrypt-proxy ;

  # Hardcoded if connection troubles
  cp $TORO2_HOMEDIR/toro2/var/cache/dnscrypt-proxy/public-resolvers.md /var/cache/dnscrypt-proxy/public-resolvers.md ;
  cp $TORO2_HOMEDIR/toro2/var/cache/dnscrypt-proxy/public-resolvers.md.minisig /var/cache/dnscrypt-proxy/public-resolvers.md.minisig ;

  # Load new resolvers (onion e.g.)
  [[ -d /tmp/dnscrypt-proxy-resolvers ]] && rm -rf /tmp/dnscrypt-proxy-resolvers ;
  mkdir -p /tmp/dnscrypt-proxy-resolvers ;
  ADD_RESOLVERS_URL="https://github.com/DNSCrypt/dnscrypt-resolvers.git" ;
  git clone $ADD_RESOLVERS_URL /tmp/dnscrypt-proxy-resolvers ;
  if [[ $? -ne 0 ]]; then
    myecho -e "  \n[\e[91m!\e[0m] Unable to get \e[91madditional resolvers\e[91m from \e[91m $ADD_RESOLVERS_URL \e[0m";
  else
    cp -i /tmp/dnscrypt-proxy-resolvers/v3/*.md /var/cache/dnscrypt-proxy/ ;
    cp -i /tmp/dnscrypt-proxy-resolvers/v3/*.md.minisig /var/cache/dnscrypt-proxy/ ;
    rm -rf /tmp/dnscrypt-proxy-resolvers ;
  fi ;
  myecho -e "[\e[92m+\e[0m] dnscrypt-proxy step 1 finish\n"

  # ----------------------------------------------------------------------------
  # End dnscrypt-proxy configuring
  # ----------------------------------------------------------------------------

  # ----------------------------------------------------------------------------
  # User settings start
  # ----------------------------------------------------------------------------
  myecho -e "[\e[93m.\e[0m] Configuring tor ... \n" ;

  # TOR_LIBDIR & TORO2_TOR_DATADIR must be owned by TOR_USER
  usermod -a -G $TORO2_USER $foruser ;

  [[ -d $TOR_LIBDIR ]] && rm -rf $TOR_LIBDIR ;
  mkdir -p $TOR_LIBDIR && chown -R $TORO2_USER: $TOR_LIBDIR && chmod 777 $TOR_LIBDIR ;
  sed -i "s!DataDirectory.*!DataDirectory $TOR_LIBDIR!" $TORO2_HOMEDIR/toro2/toro2.torrc ;
  sed -i "s/^#User=.*/User=$TORO2_USER/" $TORO2_HOMEDIR/toro2/toro2.torrc ;

  #    chmod g-s $TOR_LIBDIR
  #    sed -i "s/#DataDirectoryGroupReadable.*/DataDirectoryGroupReadable 1/g" $TORO2_HOMEDIR/toro2/toro2.torrc
  #    sed -i "s/#CacheDirectoryGroupReadable.*/CacheDirectoryGroupReadable 1/g" $TORO2_HOMEDIR/toro2/toro2.torrc

  # Allow TORO2_USER traffic runs through TOR network
  sed -i "s/^TOR_USERNAME=.*/TOR_USERNAME=$TORO2_USER/" $TORO2_HOMEDIR/toro2/toro2.iptablesA ;
  # ----------------------------------------------------------------------------
  # User settings end
  # ----------------------------------------------------------------------------

  myecho -e "[\e[93m.\e[0m] Configuring resolv.conf ... \n" ;
  if [[ -e /etc/resolv.conf ]]; then
  	if [[ -L /etc/resolv.conf ]]; then
  	    unlink /etc/resolv.conf ;
  	fi ;
    chattr -i /etc/resolv.conf && rm -f /etc/resolv.conf ;
  fi ;

  touch /etc/resolv.conf ;
  echo -e "nameserver ::1\nnameserver 127.0.0.1\noptions edns0 single-request-reopen" > /etc/resolv.conf ;
  chattr +i /etc/resolv.conf ;

  $SYSTEMCTL_BIN daemon-reload ;

  echo -e "\n[\e[92m+\e[0m] Done." ;

}

configure_$(echo "$OS_MAJOR" | tr '[:upper:]' '[:lower:]') ;
