#!/usr/bin/env python

# python script which installs
# toro2 on your system
# TORO2 sets proxy configuration equals
# privoxy + tor + iptables rules

import sys
import signal
import subprocess
import os
import shutil
import filecmp
import ast
import re


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


def check_already_installed(f):
    def wrapper(*args, **kwargs):
        try:
            if not (os.path.isdir(args[0].toro2_homedir) and os.path.exists(args[0].toro2_binary)):
                print("[-] {}, {} not found. TORO2 not installed.".format(args[0].toro2_binary, args[0].toro2_homedir))
                return False
        except Exception as e:
            return False

        return f(*args, **kwargs)

    return wrapper


class Toro2:
    def __init__(self, config_file_name="toro2.conf"):
        self.config_file_name = config_file_name
        self.config = {
            "toro2_homedir": TORO2_HOMEDIR,
            "toro2_path": TORO2_PATH,
            "toro2_binary": toro2_binary,
            "backup_osfiles": True
        }
        self.configure()

    @staticmethod
    def banner():
        banner = """

    --------[ version 2.0.1        hh15461 ]--------
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

    def backup_curr_configs(self):
        # backup_dir = [backup.0, backup.1, ..., backup.N]
        backup_dir = "{}/prev-settings.backup".format(self.toro2_homedir)
        # backup_dir = "/tmp/prev-settings.backup"
        backup_files = list(map(lambda i: i.format(os.getenv("HOME")),
                                list(filter(os.path.isdir, ["{}/.tor", "{}/.bashrc", "{}/.bashf", "{}/.bash_profile"])))) + \
                       ["/etc/dnscrypt-proxy/dnscrypt-proxy.toml", "/etc/privoxy/config", "/etc/proxychains.conf", "/etc/dnsmasq.conf"]

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

    def iptablesA(self):
        subprocess.call("{}/toro2.iptablesA".format(self.toro2_homedir))

    def iptablesD(self):
        subprocess.call("{}/toro2.iptablesD".format(self.toro2_homedir))

    @check_already_installed
    def switch_identity(self):
        try:
            tor_pid = get_pid("tor")
            os.kill(tor_pid, signal.SIGHUP)
        except Exception as e:
            print("Unable to kill tor. Is toro2 running?")

    @staticmethod
    def _kill_process(pcs):
        try:
            os.kill(get_pid(pcs), signal.SIGINT)
        except Exception as e:
            print("[-] Unable to kill {}, {}".format(pcs, e))

    @staticmethod
    def _manage_service(srv, action="status"):
        if subprocess.call("/usr/bin/systemctl {} {} >/dev/null".format(action, srv), shell=True) != 0:
            print("[-] Unable {} {}.service ... ".format(action, srv))

    def kill_tor(self):
        # check toro2.torrc for tor mode
        # if RunAsDaemon 1 then stop tor.service
        # else kill tor process
        if self.tor_as_process:
            self._kill_process("tor")
        else:
            self._manage_service("tor", "stop")

    @check_already_installed
    def status(self):
        if not self.tor_as_process:
            rservices = self.required_services + ["tor"]
        else:
            rservices = self.required_services
            tor_status = subprocess.getoutput("ps -fC tor | tail -n 1")
            print("Tor status: {}".format(tor_status))

        for rserv in rservices:
            rserv_status = subprocess.getoutput("/usr/bin/systemctl is-active {}".format(rserv))
            print("{} status: {}".format(rserv, rserv_status))

    @check_already_installed
    def stop(self):
        self.kill_tor()

        self.iptablesD()
        print('[+] iptables: delete new rules')
        for rserv in self.required_services:
            self._manage_service(rserv, "stop")
            print('[+] {} : {}'.format(rserv, "stop"))

    @check_already_installed
    def start(self):
        if self.backup_curr_configs() == 0 or not self.backup_osfiles:
            print('[+] Backup old config files (if present)')
            self.iptablesA()
            print('[+] iptables: add new rules')

            for rserv in self.required_services:
                self._manage_service(rserv, "start")
                print('[+] {} : {}'.format(rserv, "start"))

            if self.tor_as_process:
                try:
                    print("Starting tor ... ")
                    subprocess.call("/usr/bin/tor -f {}/toro2/toro2.torrc".format(self.toro2_path), shell=True)
                except KeyboardInterrupt as e:
                    self.stop()
                except Exception as e:
                    self.kill_tor()
                    self.stop()
            else:
                # tor is run as service
                self._manage_service("tor", "start")
        else:
            print('[-] Unable to backup config files')

    def os_fully_integrate(self):
        raise NotImplemented("Fully OS integration is Not implemented yet.")

    @staticmethod
    def copy_system_file(sys_file):
        if not filecmp.cmp("./{}".format(sys_file), "/{}".format(sys_file)):
            print("[.] {} ... ".format("./{}".format(sys_file)))
            shutil.copy("./{}".format(sys_file), "/{}".format(sys_file))

    def _install_dnscrypt_proxy(self):
        self.copy_system_file("usr/lib/systemd/system/dnscrypt-proxy.socket")
        self.copy_system_file("etc/dnscrypt-proxy/dnscrypt-proxy.toml")

    def _install_privoxy(self):
        self.copy_system_file("etc/privoxy/config")

    def _install_dnsmasq(self):
        self.copy_system_file("etc/dnsmasq.conf")

    def install(self, backup_osfiles=True):
        self.banner()
        # backup iptables once when installing
        self.iptables_save()
        src = os.getcwd()
        dst = self.toro2_homedir

        if not backup_osfiles:
            self.config["backup_osfiles"] = backup_osfiles
            self._write_config_file(self.config_file_name)
            self.configure()

        print("[.] Copying toro2 files ... ")
        excludes = ('os-settings.backup', '.idea', '.python-version', '.git')
        copytree(src, dst, ignore=excludes)

        print("[.] Instaling dependencies ... ")
        self._install_dnscrypt_proxy()
        self._install_privoxy()
        # self._install_dnsmasq()

        print("[.] {} ... ".format("./toro2.py"))
        shutil.copy("./toro2.py", self.toro2_binary)
        os.chmod(self.toro2_binary, 0o755)
        print("[+] Successfully installed to {}\n[+] Executable: {}".format(dst, self.toro2_binary))

    def iptables_save(self):
        if not os.path.exists("{}/iptables.superbak.lock"):
            subprocess.call("/usr/bin/iptables-save > {}/iptables.superbak".format(self.toro2_homedir), shell=True)
            subprocess.call("echo 1 > iptables.superbak.lock", shell=True)

    def iptables_restore(self):
        if os.path.exists("{}/iptables.superbak"):
            subprocess.call("/usr/bin/iptables-restore < {}/iptables.superbak".format(self.toro2_homedir), shell=True)

    @check_already_installed
    def uninstall(self):
        try:
            self.kill_tor()
            self.iptablesD()
            shutil.rmtree(self.toro2_homedir)
            if os.path.isfile(self.toro2_binary):
                os.remove(self.toro2_binary)
            print("[x] Successfully removed toro2 from {}\n[x] Executable {} removed".format(
                self.toro2_homedir, self.toro2_binary))

        except FileNotFoundError as e:
            print("[+] toro2 not installed (Project home dir {} not found)".format(self.toro2_homedir))

    def configure(self):
        if self.config:
            for k, v in self.config.items():
                self.__setattr__(k, v)

        @check_already_installed
        def _configure_tor():
            torrc = open("{}/toro2.torrc".format(self.toro2_homedir), 'r')
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
        _configure_tor()

        if self.config_file_name:
            rc = self._read_config_file()
            self.config.update(rc)
            for k, v in self.config.items():
                self.__setattr__(k, v)

    def print_config(self):
        print("{} Start: {} {}".format("-"*32, self.config_file_name, "-"*32))
        for k in self.config.keys():
            print("{:15} = {:15}".format(k, str(getattr(self, k))))

        print("{} End: {} {}".format("-"*32, self.config_file_name, "-"*32))

    def _read_config_file(self):
        config_dict = {}
        cfile_path = filter(os.path.exists, ["{}/{}".format(self.toro2_homedir, self.config_file_name), "./{}".format(self.config_file_name)])
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
            print("[-] Unable to read config from {}: {}".format(cfile_path, e))

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
            print("[-] Unable to save config to {}: {}".format(cfile_path, e))


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
            toro2.iptables_save()
        elif sys.argv[1] == "iptablesrestore":
            toro2.iptables_restore()
        elif sys.argv[1] == "integrate":
            toro2.os_fully_integrate()
        elif sys.argv[1] == "install":
            toro2.install()
        elif sys.argv[1] == "installnobackup":
            toro2.install(backup_osfiles=False)
        elif sys.argv[1] == "uninstall":
            toro2.uninstall()
            del toro2
        elif sys.argv[1] == "help":
            help()
        else:
            print("[-] Unknown '{}'.".format(sys.argv[1]))
    else:
        help()
