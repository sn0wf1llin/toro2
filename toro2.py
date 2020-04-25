#!/usr/bin/env python

# python script which installs
# toro2 on your system
# TORO2 sets proxy configuration equals
# privoxy + tor + iptables rules

import subprocess
import sys
import os
import signal
import shutil

TORO2_PATH = "/etc"
TORO2_HOMEDIR = "{}/toro2".format(TORO2_PATH)
toro2_bin = "/usr/bin/toro2"


# def os_exec(command, error_handler=None, error_code=1, shell=False):
#     res = subprocess.call(command, shell=shell)
#
#     if res != 0:
#         print("Unable to execute {}".format(command))
#         if error_handler is not None:
#             error_handler(error_code)
#

def banner():
    banner = """

        #############################################
        #                                           #
        #  Tor + privoxy + iptables + DNS-via-Tor   #
        #                                           #
        #############################################
    	  ________   ___ _    ___ _     ___ _                                 
    	 /__  ___/ //   ) ) //   ) )  //   ) ) ___    
    	   / /    //   / / //___/ /  //   / ///   ) ) 
    	  / /    //   / / / ___ (   //   / /  ___/ /  
    	 / /    //   / / //   | |  //   / / / ____/   
    	/_/    ((___/ / //    |_| ((___/ / / /____    
    	                                  /______/ 

    """
    print(banner)


def check_installed(f):
    # if not (os.path.isdir(TORO2_HOMEDIR) and os.path.exists(toro2_bin)):
    #     print("[-] {}, {} not found. TORO2 not installed.".format(toro2_bin, TORO2_HOMEDIR))
    #     exit(1)

    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


def get_pid(name):
    return int(subprocess.check_output(["pidof", name]))


def copytree(src, dst, symlinks=False, ignore=None):
    if not os.path.isdir(dst):
        os.makedirs(dst)

    for item in os.listdir(src):
        if ignore is not None:
            if item in ignore:
                continue

        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d):
                shutil.copy2(s, d)


def backup_curr_configs():
    # backup_dir = [backup.0, backup.1, ..., backup.N]
    backup_dir = "{}/prev-settings.backup".format(TORO2_HOMEDIR)
    # backup_dir = "/tmp/prev-settings.backup"
    backup_files = list(map(lambda i: i.format(os.getenv("HOME")),
                            ["{}/.tor", "{}/.bashrc", "{}/.bashf", "{}/.bash_profile"])) + \
                   ["/etc/dnscrypt-proxy/dnscrypt-proxy.toml", "/etc/privoxy/config", "/etc/proxychains.conf"]

    limit_backup_dirN = 5
    subfolders = []

    if os.path.exists(backup_dir):
        subfolders_fullpath = [f.path for f in os.scandir(backup_dir) if f.is_dir()]
        subfolders = [i.split('/')[-1] for i in subfolders_fullpath]
        if len(subfolders) > 0:
            subfolders.sort()
            try:
                curr_backup_dir_n = int(subfolders[-1].split('.')[1]) + 1
            except TypeError as e:
                curr_backup_dir_n = 0
        else:
            curr_backup_dir_n = 0

    else:
        os.makedirs(backup_dir)
        curr_backup_dir_n = 0

    if curr_backup_dir_n >= limit_backup_dirN and len(subfolders) == limit_backup_dirN:
        shutil.rmtree("{}/{}".format(backup_dir, subfolders[-1]))  # , ignore_errors=True)

        for f in reversed(subfolders[:-1]):
            dst = "{}/backup.{}".format(backup_dir, int(f.split('.')[1]) + 1)
            shutil.copytree("{}/{}".format(backup_dir, f), dst)
            shutil.rmtree("{}/{}".format(backup_dir, f))

        curr_backup_dir_n = 0
        shutil.rmtree("{}/backup.{}".format(backup_dir, 0), ignore_errors=True)

    curr_backup_dir = "backup.{}".format(str(curr_backup_dir_n))
    os.makedirs("{}/{}".format(backup_dir, curr_backup_dir))

    for item in backup_files:
        if os.path.isdir(item):
            dir_name = item.split('/')[-1]
            copytree(item, "{}/{}/{}".format(backup_dir, curr_backup_dir, dir_name))
        else:
            shutil.copy2(item, "{}/{}/".format(backup_dir, curr_backup_dir))

    command = "/usr/bin/iptables-save > BAKDIR/iptables.bak && /usr/bin/ip6tables-save > BAKDIR/ip6tables.bak".replace(
        "BAKDIR", "{}/{}".format(backup_dir, curr_backup_dir))

    return subprocess.call(command, shell=True)


def iptablesA():
    command = "{}/toro2.iptablesA".format(TORO2_HOMEDIR)
    subprocess.call(command)


def iptablesD():
    command = "{}/toro2.iptablesD".format(TORO2_HOMEDIR)
    subprocess.call(command)


@check_installed
def switch_identity():
    tor_pid = get_pid("tor")
    os.kill(tor_pid, signal.SIGHUP)


@check_installed
def start():
    if backup_curr_configs() == 0:
        print('[+] Backup old config files (if present)')
        iptablesA()
        print('[+] iptables: add new rules')
        subprocess.call("/usr/bin/systemctl start privoxy", shell=True)
        print('[+] privoxy started')
        subprocess.call("/usr/bin/tor -f {}/toro2/toro2.torrc".format(TORO2_PATH), shell=True)
    else:
        print('[-] Unable to backup config files')


@check_installed
def stop():
    try:
        os.kill(get_pid("tor"), signal.SIGINT)
    except Exception as e:
        print("[-] Unable to kill tor, {}".format(e))
    iptablesD()
    print('[+] iptables: delete new rules')
    subprocess.call("/usr/bin/systemctl stop privoxy", shell=True)
    print('[+] privoxy stopped')


def os_fully_integrate():
    raise NotImplemented("Fully OS integration is Not implemented yet.")


def install():
    banner()
    src = os.getcwd()
    dst = TORO2_HOMEDIR
    excludes = ('os-settings.backup', '.idea', '.python-version', 'settings.txt')

    copytree(src, dst, ignore=excludes)
    shutil.copy("./toro2.py", toro2_bin)
    os.chmod(toro2_bin, 0o755)
    print("[+] Successfully installed to {}\n[+] Executable: {}".format(dst, toro2_bin))


def uninstall():
    try:
        shutil.rmtree(TORO2_HOMEDIR)
        if os.path.isfile(toro2_bin):
            os.remove(toro2_bin)
        print("[x] Successfully removed toro2 from {}\n[x] Executable {} removed".format(TORO2_HOMEDIR, toro2_bin))

    except FileNotFoundError as e:
        print("[+] toro2 not installed (Project home dir {} not found)".format(TORO2_HOMEDIR))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "stop":
            stop()
        elif sys.argv[1] == "switch":
            switch_identity()
        elif sys.argv[1] == "start":
            start()
        elif sys.argv[1] == "integrate":
            os_fully_integrate()
        elif sys.argv[1] == "install":
            install()
        elif sys.argv[1] == "uninstall":
            uninstall()
        else:
            print("[-] '{}' wrong.")
    else:
        print("Usage: toro2 stop|switch|start|integrate|install|uninstall")
