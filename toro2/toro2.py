# python script which installs
# toro2 on your system
# TORO2 sets proxy configuration equals
# privoxy + tor + iptables rules

import sys
import glob
import signal
import subprocess
import os
import shutil
import filecmp
import ast
import re
import csv
import grp


class bgcolors:
    RESET_COLOR = "\033[0m"
    LIGHT_RED_COLOR = "\033[91m"
    LIGHT_GREEN_COLOR = "\033[92m"
    LIGHT_YELLOW_COLOR = "\033[93m"
    LIGHT_BLUE_COLOR = "\033[94m"
    LIGHT_MAGENTA_COLOR = "\033[95m"
    LIGHT_CYAN_COLOR = "\033[96m"
    LIGHT_GRAY_COLOR = "\033[37m"

    RED_COLOR = "\033[31m"
    GREEN_COLOR = "\033[32m"
    YELLOW_COLOR = "\033[33m"
    BLUE_COLOR = "\033[34m"
    MAGENTA_COLOR = "\033[35m"
    CYAN_COLOR = "\033[36m"
    WHITE_COLOR = "\033[97m"

# try:
#     import termcolor
# except ModuleNotFoundError:
#     subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'termcolor'], stdout=subprocess.DEVNULL)
#     import importlib
#     importlib.import_module('termcolor')
#
# from termcolor import colored, cprint

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


def help():
    print("""
Usage: toro2 [start] [stop] [switch] [install] [uninstall]
        [status] [integrate] [installnobackup]
        [iptablessave] [iptablesrestore]
        start                Start toro2 app (required to have it INSTALLed first)
        stop                 Stop toro2 app (stop services & tor)
        switch               Switch tor identity
        install              Install toro2 app & files
        uninstall            Uinstall toro2 app & files
        status               Get state of tor & services
        integrate            Integrate toro2 installation with OS
        installnobackup      Same as INSTALL, with no backup system files
        iptablessave         Save iptables configuration
        iptablesrestore      Restore iptables configuration
    """)


TORO2_PATH = "/etc"
TORO2_HOMEDIR = "{}/toro2".format(TORO2_PATH)
toro2_binary = "/usr/bin/toro2"


def get_os_release():
    release = {}
    with open('/etc/os-release') as f:
        reader = csv.reader(f, delimiter="=")
        for row in reader:
            if row:
                release[row[0]] = row[1]

    return release

def check_already_installed(f):
    def wrapper(*args, **kwargs):
        try:
            if not (os.path.isdir(args[0].toro2_homedir) or os.path.exists(args[0].toro2_binary)) and f.__name__ != 'install':
                #print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] {args[0].toro2_binary} (or) {args[0].toro2_homedir} not found. TORO2 not installed.')
                return None
        except Exception as e:
            print(e)
            return None

        return f(*args, **kwargs)

    return wrapper


class Toro2:
    def __init__(self, config_file_name="toro2.conf"):
        self.config_file_name = config_file_name
        self.files_to_backup = list(map(lambda i: i.format(os.getenv("HOME")),
                                list(filter(os.path.exists, ["{}/.tor", "{}/.bashrc",
                                "{}/.bashf", "{}/.bash_profile",
                                "/etc/dnscrypt-proxy/dnscrypt-proxy.toml",
                                "/etc/privoxy/config", "/etc/proxychains.conf",
                                "/etc/dnsmasq.conf"]))))
        self.config = {
            "toro2_stuff_homedir": "{}/.toro2".format(TORO2_HOMEDIR),
            "toro2_homedir": TORO2_HOMEDIR,
            "toro2_path": TORO2_PATH,
            "toro2_binary": toro2_binary,
            "backup_osfiles": True,
            "pidfile": "/tmp/toro2.pid"
        }

        self.configure()

        if self.backup_osfiles:
            self.backup_curr_configs = self.backup_curr_configs_dummy
        else:
            self.backup_curr_configs = self._backup_curr_configs

        try:
            int(subprocess.getoutput("id -u {}".format(self.username)))
        except ValueError:
            self.user("toro2", "create")

    @staticmethod
    def get_system_user():
        return subprocess.getoutput('id -un')

    @staticmethod
    def banner():
        banner = """

    --------[ version 2.1.0        hh15461 ]--------
    --------[ Breathe freely with    TorO2 ]--------

    ###############################################
    #                                             #
    #  Tor + privoxy + iptables + dnscrypt-proxy  #
    #                                             #
    ###############################################
       ________   ___ _    ___ _     ___ _
      /__  ___/ //   ) ) //   ) )  //   ) ) ___
        / /    //   / / //___/ /  //   / ///   ) )
       / /    //   / / / ___ (   //   / /  ___/ /
      / /    //   / / //   | |  //   / / / ____/
     /_/    ((___/ / //    |_| ((___/ / / /____
                                       /______/

        """
        print(banner)

    def backup_curr_configs_dummy(self):
        print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] {bgcolors.LIGHT_YELLOW_COLOR}Attention{bgcolors.RESET_COLOR}: no backup for system files')

    def _backup_curr_configs(self):
        # backup_dir = [backup.0, backup.1, ..., backup.N]
        backup_dir = "{}/prev-settings.backup".format(self.toro2_stuff_homedir)
        # backup_dir = "/tmp/prev-settings.backup"
        limit_backup_dirN = 2
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
            subprocess.call("mkdir {}".format(backup_dir), shell=True)
            os.chown(backup_dir, self.uid, self.gid)
            # os.makedirs(backup_dir)
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
        try:
            os.makedirs("{}/{}".format(backup_dir, curr_backup_dir))
        except PermissionError:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Trouble with makedir {"{}/{}".format(backup_dir, curr_backup_dir)}')

        os.chown("{}/{}".format(backup_dir, curr_backup_dir), self.uid, self.gid)

        for item in self.files_to_backup:
            if os.path.isdir(item):
                dir_name = item.split('/')[-1]
                copytree(item, "{}/{}/{}".format(backup_dir, curr_backup_dir, dir_name))
            else:
                shutil.copy2(item, "{}/{}/".format(backup_dir, curr_backup_dir))

        command = "{} > BAKDIR/iptables.bak && {} > BAKDIR/ip6tables.bak".format(
            self.iptables_save, self.ip6tables_save).replace(
            "BAKDIR", "{}/{}".format(backup_dir, curr_backup_dir))

        try:
            subprocess.call("sudo -u {} {}".format(self.username, command), shell=True)
        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to execute {bgcolors.LIGHT_YELLOW_COLOR}{command}{bgcolors.RESET_COLOR} : {e}')

    def iptablesA(self):
        bad_ifaces = ['lo']
        out_ifaces = "".join(i + " " for i in os.listdir('/sys/class/net') if i not in bad_ifaces)[:-1]
        if self.get_system_user() == 'root':
            subprocess.call("{}/toro2/toro2.iptablesA".format(self.toro2_homedir), shell=True)
        else:
            subprocess.call("sudo {}/toro2/toro2.iptablesA".format(self.toro2_homedir), shell=True)

    def iptablesD(self):
        if self.get_system_user() == 'root':
            subprocess.call("{}/toro2/toro2.iptablesD".format(self.toro2_homedir), shell=True)
        else:
            subprocess.call("sudo {}/toro2/toro2.iptablesD".format(self.toro2_homedir), shell=True)

    @check_already_installed
    def switch_identity(self):
        try:
            tor_pid = get_pid("tor")
            os.kill(tor_pid, signal.SIGHUP)
        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to kill {bgcolors.LIGHT_YELLOW_COLOR}tor{bgcolors.RESET_COLOR} : {e}')

    @staticmethod
    def _kill_process(pcs):
        try:
            os.kill(get_pid(pcs), signal.SIGINT)
        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to kill {bgcolors.LIGHT_YELLOW_COLOR}{pcs}{bgcolors.RESET_COLOR} : {e}')

    def _manage_service(self, srv, action="status"):
        command = "{} {} {} >/dev/null".format(self.systemctl, action, srv)
        if self.get_system_user() != 'root':
            command = "sudo {}".format(command)

        retcode = subprocess.call(command , shell=True)
        if retcode != 0:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR}{action}{bgcolors.RESET_COLOR} {srv}.service ... ')
        return retcode

    def kill_tor(self):
        # check toro2.torrc for tor mode
        # if RunAsDaemon 1 then stop tor.service
        # else kill tor process
        if self.tor_as_process:
            subprocess.call('sudo killall tor', shell=True)
            # self._kill_process("tor")
        else:
            self._manage_service("tor", "stop")

    @check_already_installed
    def status(self):
        outcode = 1
        try:
            outcode = subprocess.check_call("ps aux | grep toro2 | grep -v grep",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        except Exception as e:
            pass

        if not self.tor_as_process:
            rservices = self.required_services + ["tor"]
        else:
            rservices = self.required_services
            tor_status = subprocess.getoutput("ps -fC tor | tail -n 1 | grep -v PPID || echo 'no info'")
            if tor_status == 'no info':
                print(f'Tor status: \n\t{bgcolors.YELLOW_COLOR}{tor_status}{bgcolors.RESET_COLOR}')
            else:
                print(f'Tor status: \n\t{tor_status}')

        for rserv in rservices:
            rserv_status = subprocess.getoutput("{} is-active {}".format(self.systemctl, rserv))
            if rserv_status == 'active':
                print(f'{rserv} status: \n\t{bgcolors.GREEN_COLOR}{rserv_status}{bgcolors.RESET_COLOR}')
            else:
                print(f'{rserv} status: \n\t{bgcolors.RED_COLOR}{rserv_status}{bgcolors.RESET_COLOR}')

        return outcode

    @check_already_installed
    def stop(self):
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)

        self.kill_tor()

        # delete iptables.superbak.lock & ip6tables.superbak.lock files
        if os.path.exists("{}/iptables.superbak.lock".format(self.toro2_homedir)):
            try:
                os.remove("{}/iptables.superbak.lock".format(self.toro2_homedir))
            except Exception as e:
                subprocess.call("sudo -u {} rm -f {}/iptables.superbak.lock".format(self.username, self.toro2_homedir), shell=True)

        if os.path.exists("{}/ip6tables.superbak.lock".format(self.toro2_homedir)):
            try:
                os.remove("{}/ip6tables.superbak.lock".format(self.toro2_homedir))
            except Exception as e:
                subprocess.call("sudo -u {} rm -f {}/ip6tables.superbak.lock".format(self.username, self.toro2_homedir), shell=True)

        self.iptablesD()

        print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] {bgcolors.WHITE_COLOR}iptables{bgcolors.RESET_COLOR}: {bgcolors.YELLOW_COLOR}delete{bgcolors.RESET_COLOR} new rules')

        rserv_retcode = 0
        stopped = []
        for rserv in self.required_services:
            rserv_retcode ^= self._manage_service(rserv, "stop")
            if rserv_retcode == 0:
                stopped.append(rserv)
                print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] {bgcolors.WHITE_COLOR}{rserv}{bgcolors.RESET_COLOR} : stop')
            else:
                print(f'[{bgcolors.RED_COLOR}-{bgcolors.RESET_COLOR}] {bgcolors.WHITE_COLOR}{rserv}{bgcolors.RESET_COLOR} : Unable to stop')

    @check_already_installed
    def start(self):
        def start_tor():
            if self.tor_as_process:
                command = "{} -f {}/toro2/toro2.torrc".format(self.tor, self.toro2_homedir)
                if self.get_system_user() != 'root':
                    command = "sudo -u {} {}".format(self.username, command)
                try:
                    print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Starting {bgcolors.WHITE_COLOR}tor{bgcolors.RESET_COLOR} ... ')
                    subprocess.call(command, shell=True)
                except KeyboardInterrupt as e:
                    self.stop()
                except Exception as e:
                    self.kill_tor()
                    self.stop()
            else:
                # tor is run as service
                self._manage_service("tor", "start")

        if not os.path.exists(self.pidfile):
            with open(self.pidfile, 'w') as f: f.write(str(os.getpid()))

            self.backup_curr_configs()

            self.iptablesA()

            print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] {bgcolors.WHITE_COLOR}iptables{bgcolors.RESET_COLOR}: {bgcolors.GREEN_COLOR}add{bgcolors.RESET_COLOR} new rules')

            rserv_retcode = 0
            started = []
            for rserv in self.required_services:
                rserv_retcode ^= self._manage_service(rserv, "start")
                if rserv_retcode == 0:
                    started.append(rserv)
                    print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] {bgcolors.WHITE_COLOR}{rserv}{bgcolors.RESET_COLOR} : start')
                else:
                    print(f'[{bgcolors.RED_COLOR}-{bgcolors.RESET_COLOR}] {bgcolors.WHITE_COLOR}{rserv}{bgcolors.RESET_COLOR} : Unable to start')

            if rserv_retcode == 0:
                start_tor()
            else:
                # smth happened => stop those services which are already started
                for sserv in started:
                    if self._manage_service(sserv, "stop") == 0:
                        print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] {bgcolors.WHITE_COLOR}{rserv}{bgcolors.RESET_COLOR} : stop')
        else:
            with open(self.pidfile,'r') as f: pid = f.readline().strip()
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Toro2 already started PID {bgcolors.LIGHT_YELLOW_COLOR} {pid} {bgcolors.RESET_COLOR}')

    def os_fully_integrate(self):
        print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Fully OS integration is {bgcolors.LIGHT_YELLOW_COLOR}Not implemented yet{bgcolors.RESET_COLOR}')

    def copy_system_file(self, sys_file, dst=None):
        if dst is None:
            dst = "/{}".format(sys_file)

        try:
            subprocess.call("sudo cp {} {}".format("{}/{}".format(os.getcwd(), sys_file), dst), shell=True)
            print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] {bgcolors.WHITE_COLOR}{sys_file} --> {dst}{bgcolors.RESET_COLOR}: {bgcolors.LIGHT_GREEN_COLOR}success{bgcolors.RESET_COLOR}')

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Troubles while copying {sys_file} to {dst} : {e}')

    def _install_dnscrypt_proxy(self):
        dnscrypt_sok_file = "usr/lib/systemd/system/dnscrypt-proxy.socket"
        dnscrypt_srv_file = "usr/lib/systemd/system/dnscrypt-proxy.service"
        dnscrypt_toml_file = "etc/dnscrypt-proxy/dnscrypt-proxy.toml"

        if get_os_release()["ID"].lower() == "arch":
            self.copy_system_file(sys_file=f'toro2/{dnscrypt_srv_file}', dst=f'/{dnscrypt_srv_file}')
            self.copy_system_file(sys_file=f'toro2/{dnscrypt_sok_file}', dst=f'/{dnscrypt_sok_file}')

        elif get_os_release()["ID"].lower() in ["ubuntu", "kali", "linuxmint"]:
            self.copy_system_file(sys_file=f'toro2/{dnscrypt_srv_file}', dst="/lib/systemd/system/dnscrypt-proxy.service")
            self.copy_system_file(sys_file=f'toro2/{dnscrypt_sok_file}', dst='/lib/systemd/system/dnscrypt-proxy.socket')

        else:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable to copy {dnscrypt_srv_file} : {bgcolors.LIGHT_YELLOW_COLOR}not implemented for your OS release{bgcolors.RESET_COLOR} : {get_os_release()["ID"]}')

        self.copy_system_file(sys_file=f'toro2/{dnscrypt_toml_file}', dst=f'/{dnscrypt_toml_file}')

    def _install_privoxy(self):
        privoxy_srv_file = "usr/lib/systemd/system/privoxy.service"

        if get_os_release()["ID"].lower() == "arch":
            self.copy_system_file(sys_file=f'toro2/{privoxy_srv_file}', dst=f'/{privoxy_srv_file}')

        elif get_os_release()["ID"].lower() in ["ubuntu", "kali", "linuxmint"]:
            self.copy_system_file(sys_file=f'toro2/{privoxy_srv_file}', dst="/lib/systemd/system/privoxy.service")

        else:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable to copy {privoxy_srv_file} : {bgcolors.LIGHT_YELLOW_COLOR}not implemented for your OS release{bgcolors.RESET_COLOR} : {get_os_release()["ID"]}')

        try:
            copytree('toro2/etc/privoxy/templates', '/etc/privoxy/templates')
            privoxy_files_list = ['etc/privoxy/default.action', 'etc/privoxy/default.filter', 'etc/privoxy/match-all.action', 'etc/privoxy/regression-tests.action', 'etc/privoxy/trust', 'etc/privoxy/user.action', 'etc/privoxy/user.filter', 'etc/privoxy/config']
            for pf in privoxy_files_list:
                self.copy_system_file(sys_file=f'toro2/{pf}', dst=f'/{pf}')

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] {e}')

    def _install_dnsmasq(self):
        dnsm_conf = "etc/dnsmasq.conf"
        self.copy_system_file(sys_file=f'toro2/{dnsm_conf}', dst=f'/{dnsm_conf}')

    def user(self, username, action):
        if action == "create":
            #subprocess.call("groupadd -r {}".format(username), shell=True)
            subprocess.call("useradd --system --shell /bin/false --no-create-home {}".format(username), shell=True)
            self.username = username
            self.uid = int(subprocess.getoutput("id -u {}".format(self.username)))
            self.gid = int(subprocess.getoutput("id -g {}".format(self.username)))

        elif action == "delete":
            subprocess.call("userdel {}".format(username), shell=True)
            try:
                grp.getgrnam(username)
                subprocess.call("groupdel {}".format(username), shell=True)
            except KeyError: pass
            self.username = None
        elif action == "getuid":
            return int(subprocess.getoutput("id -u {}".format(self.username)))
        elif action == "getgid":
            return int(subprocess.getoutput("id -g {}".format(self.username)))

    @check_already_installed
    def install(self, backup_osfiles_ultimate=True):
        self.banner()

        if not os.path.isdir(self.toro2_homedir):
            os.makedirs(self.toro2_homedir)

        # backup iptables once when installing
        self._iptables_save()
        src = os.getcwd()
        dst = self.toro2_homedir

        if backup_osfiles_ultimate:
            self.config["backup_osfiles"] = backup_osfiles
            self._write_config_file(self.config_file_name)
            self.configure()

        print(f'[{bgcolors.LIGHT_GRAY_COLOR}.{bgcolors.RESET_COLOR}] Copying toro2 files ... ')
        excludes = ('.idea', '.python-version', '.git', 'toro2/etc', 'toro2/usr', '.gitignore', 'install.sh')
        copytree(src, dst, ignore=excludes)

        print(f'[{bgcolors.LIGHT_GRAY_COLOR}.{bgcolors.RESET_COLOR}] Installing dependencies ... ')
        # call installing functions defined by serviced required
        for rs in self.required_services:
            if 'socket' not in rs:
                try:
                    serv_install_func = getattr(self, '_install_{}'.format(rs.replace('-', '_')))
                    serv_install_func()

                except Exception as e:
                    print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Can\'t install {bgcolors.LIGHT_YELLOW_COLOR}{rs}{bgcolors.RESET_COLOR} : possible absense {bgcolors.LIGHT_MAGENTA_COLOR}{"_install_{}".format(rs.replace("-", "_"))}{bgcolors.RESET_COLOR} installation function : {e}')

        print(f'[{bgcolors.LIGHT_GRAY_COLOR}.{bgcolors.RESET_COLOR}] {"{}/toro2/toro2".format(os.getcwd())} to {self.toro2_binary} ... ')
        shutil.copy("{}/toro2/toro2".format(os.getcwd()), self.toro2_binary)
        os.chmod(self.toro2_binary, 0o755)
        try:
            # os.chown(self.toro2_binary, self.uid, self.gid)
            os.chown(self.toro2_homedir, self.user(self.username, 'getuid'), self.user(self.username, 'getgid'))
            subprocess.call("chown {}: {}/*".format(self.username, self.toro2_homedir), shell=True)
            subprocess.call("chown root {}/toro2/toro2.iptables*".format(self.toro2_homedir), shell=True)
            subprocess.call("chmod u+s {}/toro2/toro2.iptables*".format(self.toro2_homedir), shell=True)

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to set attrs for {self.toro2_homedir}/* {bgcolors.LIGHT_YELLOW_COLOR}or{bgcolors.RESET_COLOR} {self.toro2_homedir}/toro2/toro2.iptables* : {e}')

        print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Successfully installed to {dst}')
        print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Executable: {self.toro2_binary}')

    def _iptables_save(self):
        try:
            # if iptables.superbak.lock & ip6tables.superbak.lock files exist => iptables were saved BEFORE
            # they changed via TORO2-rules, so, no need to save those ones
            if not os.path.exists("{}/iptables.superbak.lock".format(self.toro2_homedir)):
                subprocess.call("{} > {}/iptables.superbak".format(self.iptables_save, self.toro2_homedir), shell=True)
                subprocess.call("echo 1 > {}/iptables.superbak.lock".format(self.toro2_homedir), shell=True)

            if not os.path.exists("{}/ip6tables.superbak.lock".format(self.toro2_homedir)):
                subprocess.call("{} > {}/ip6tables.superbak".format(self.ip6tables_save, self.toro2_homedir), shell=True)
                subprocess.call("echo 1 > {}/ip6tables.superbak.lock".format(self.toro2_homedir), shell=True)

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to save iptables & ip6tables : {e}')

    def _iptables_restore(self):
        try:
            if os.path.exists("{}/iptables.superbak".format(self.toro2_homedir)):
                subprocess.call("{} < {}/iptables.superbak".format(self.iptables_restore, self.toro2_homedir), shell=True)
            if os.path.exists("{}/ip6tables.superbak".format(self.toro2_homedir)):
                subprocess.call("{} < {}/ip6tables.superbak".format(self.ip6tables_restore, self.toro2_homedir), shell=True)
        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to restore iptables & ip6tables : {e}')

    @check_already_installed
    def uninstall(self):
        try:
            if self.status != 0:
                self.stop()
            # self.kill_tor()
            # self.iptablesD()
            try:
                shutil.rmtree(self.toro2_homedir)
                print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Clean {self.toro2_homedir} ... ')

                if os.path.isdir(f'{self.toro2_stuff_homedir}'):
                    shutil.rmtree(self.toro2_stuff_homedir)
                    print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Clean {self.toro2_stuff_homedir} ... ')

                # if os.path.isdir(f'/home/{self.get_system_user()}/.toro2'):
                #     d = f'/home/{self.get_system_user()}/.toro2'
                #     shutil.rmtree(d)
                #     print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Clean {d} ... ')

            except Exception as e:
                print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] {e}')

            if os.path.isfile(self.toro2_binary):
                os.remove(self.toro2_binary)
                print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Executable {self.toro2_binary} removed')

            #shutil.rmtree("/opt/toro2")
            self.user("toro2", "delete")

        except FileNotFoundError as e:
            print(f'[{bgcolors.LIGHT_CYAN_COLOR}+/-{bgcolors.RESET_COLOR}] toro2 not installed\n{e}')

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] {e}')

    @check_already_installed
    def _configure_tor(self):
        try:
            torrc = open("{}/toro2/toro2.torrc".format(self.toro2_homedir), 'r')
        except Exception: return
        torrc_data = torrc.read()
        torrc.close()

        if "RunAsDaemon" in re.findall(r'#.*', torrc_data):
            # if RunAsDaemon commented => run tor as a process
            self.tor_as_process = True
        else:
            daemon_param = re.findall(r'RunAsDaemon.*', torrc_data)
            if daemon_param:
                dp_val = int(re.findall(r'\d', daemon_param[0])[0])
                if dp_val == 1:
                    # tor is run as service
                    self.tor_as_process = False
                else:
                    # tor is a process
                    self.tor_as_process = True

    def configure(self):
        if self.config:
            for k, v in self.config.items():
                setattr(self, k, v)

        self._configure_tor()

        if self.config_file_name:
            rc = self._read_config_file()
            self.config.update(rc)
            for k, v in self.config.items():
                setattr(self, k, v)

    def print_config(self):
        print("{} Start: {} {}".format("-"*32, self.config_file_name, "-"*32))
        for k in self.config.keys():
            print("{:15} = {:15}".format(k, str(getattr(self, k))))

        print("{} End: {} {}".format("-"*32, self.config_file_name, "-"*32))

    def _read_config_file(self):
        config_dict = {}
        cfile_path = list(filter(os.path.exists, [
            "{}/toro2/{}".format(self.toro2_homedir, self.config_file_name),
            "{}/{}".format(os.getcwd(), self.config_file_name),
            "{}/toro2/{}".format(os.getcwd(), self.config_file_name)]))
        try:
            with open(list(cfile_path)[0], 'r') as config:
                for cline in config.readlines():
                    li = cline.strip()
                    if li.startswith("#"):
                        continue
                    data = li.split("=")
                    val = data[1]
                    if '[' in val:
                        val = ast.literal_eval(val.strip())

                    config_dict[data[0]] = val

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to read config from {cfile_path} : {e}')

        return config_dict

    def _write_config_file(self, config_file_name):
        if config_file_name is None:
            config_file_name = self.config_file_name

        cfile_path = "{}/{}".format(self.toro2_homedir, config_file_name)

        try:
            with open(cfile_path, 'w') as config:
                for k, v in self.config.items():
                    cline = "{}={}\n".format(k, v)
                    config.write(cline)

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to save config to {cfile_path} : {e}')


if __name__ == "__main__":
    toro2 = Toro2()

    if len(sys.argv) > 1:
        if sys.argv[1] == "stop":
            toro2.stop()
        elif sys.argv[1] == "switch":
            toro2.switch_identity()
        elif sys.argv[1] == "start":
            toro2.start()
        elif sys.argv[1] == "status":
            toro2.status()
        elif sys.argv[1] == "iptablessave":
            toro2._iptables_save()
        elif sys.argv[1] == "iptablesrestore":
            toro2._iptables_restore()
        elif sys.argv[1] == "integrate":
            toro2.os_fully_integrate()
        elif sys.argv[1] == "install":
            toro2.install()
        elif sys.argv[1] == "installnobackup":
            toro2.install(backup_osfiles_ultimate=False)
        elif sys.argv[1] == "uninstall":
            toro2.uninstall()
            del toro2
        elif sys.argv[1] == "help":
            help()
        else:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unknown \'{sys.argv[1]}\'')
    else:
        help()
