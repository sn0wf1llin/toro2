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


TORO2_PATH = "/etc"
TORO2_HOMEDIR = "{}/toro2".format(TORO2_PATH)
toro2_binary = "/usr/bin/toro2"


def check_already_installed(f):
    def wrapper(*args, **kwargs):
        if not (os.path.isdir(args[0].toro2_homedir) and os.path.exists(args[0].toro2_binary)):
            print("[-] {}, {} not found. TORO2 not installed.".format(args[0].toro2_binary, args[0].toro2_homedir))
            return False
        return f(*args, **kwargs)

    return wrapper


class Toro2:
    def __init__(self, config_file_name="toro2.conf"):
        self.config_file_name = config_file_name

        self.config = dict()
        self.init_config()
        self.update_config()

    @staticmethod
    def banner():
        banner = """

    ----[ version 2.0        hh15461 ]----
    ----[ Breathe freely with TorO2  ]----

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

    def backup_curr_configs(self):
        # backup_dir = [backup.0, backup.1, ..., backup.N]
        backup_dir = "{}/prev-settings.backup".format(self.toro2_homedir)
        # backup_dir = "/tmp/prev-settings.backup"
        backup_files = list(map(lambda i: i.format(os.getenv("HOME")),
                                list(filter(os.path.isdir, ["{}/.tor", "{}/.bashrc", "{}/.bashf", "{}/.bash_profile"])))) + \
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

    def iptablesA(self):
        command = "{}/toro2.iptablesA".format(self.toro2_homedir)
        subprocess.call(command)

    def iptablesD(self):
        command = "{}/toro2.iptablesD".format(self.toro2_homedir)
        subprocess.call(command)

    @check_already_installed
    def switch_identity(self):
        tor_pid = get_pid("tor")
        os.kill(tor_pid, signal.SIGHUP)

    @staticmethod
    def kill_tor():
        try:
            os.kill(get_pid("tor"), signal.SIGINT)
        except Exception as e:
            print("[-] Unable to kill tor, {}".format(e))

    @check_already_installed
    def stop(self):
        # self.kill_tor()

        self.iptablesD()
        print('[+] iptables: delete new rules')
        subprocess.call("/usr/bin/systemctl stop privoxy", shell=True)
        print('[+] privoxy stopped')

    @check_already_installed
    def start(self):
        if self.backup_curr_configs() == 0:
            print('[+] Backup old config files (if present)')
            self.iptablesA()
            print('[+] iptables: add new rules')
            subprocess.call("/usr/bin/systemctl start privoxy", shell=True)
            print('[+] privoxy started')
            try:
                subprocess.call("/usr/bin/tor -f {}/toro2/toro2.torrc".format(self.toro2_path), shell=True)
            except KeyboardInterrupt as e:
                self.stop()
            except Exception as e:
                self.kill_tor()
                self.stop()
        else:
            print('[-] Unable to backup config files')

    def os_fully_integrate(self):
        raise NotImplemented("Fully OS integration is Not implemented yet.")

    def install(self, backup_osfiles=True):
        self.banner()
        src = os.getcwd()
        dst = self.toro2_homedir

        if not backup_osfiles:
            self.config["backup_osfiles"] = backup_osfiles
            self.write_config_file(self.config_file_name)
            self.update_config()

        excludes = ('os-settings.backup', '.idea', '.python-version', 'settings.txt')

        copytree(src, dst, ignore=excludes)
        shutil.copy("./toro2.py", self.toro2_binary)
        os.chmod(self.toro2_binary, 0o755)
        print("[+] Successfully installed to {}\n[+] Executable: {}".format(dst, self.toro2_binary))

    @check_already_installed
    def uninstall(self):
        try:
            self.iptablesD()
            shutil.rmtree(self.toro2_homedir)
            if os.path.isfile(self.toro2_binary):
                os.remove(self.toro2_binary)
            print("[x] Successfully removed toro2 from {}\n[x] Executable {} removed".format(
                self.toro2_homedir, self.toro2_binary))

        except FileNotFoundError as e:
            print("[+] toro2 not installed (Project home dir {} not found)".format(self.toro2_homedir))

    def init_config(self):
        self.config = {
            "toro2_homedir": TORO2_HOMEDIR,
            "toro2_path": TORO2_PATH,
            "toro2_binary": toro2_binary,
            "backup_osfiles": True
        }

    def print_config(self):
        print("{} Start: {} {}".format("-"*32, self.config_file_name, "-"*32))
        for k, v in self.config.items():
            print("{:15} = {:15}".format(k, v))

        print("{}  End   {} {}".format("-"*32, self.config_file_name, "-"*32))

    def update_config(self):
        rc = self.read_config_file()
        self.config.update(rc)

        if self.config:
            for k, v in self.config.items():
                self.__setattr__(k, v)

    def read_config_file(self, config_file_name=None):
        if config_file_name is None:
            config_file_name = self.config_file_name

        config_dict = {}
        try:
            cfile_path = "{}/{}".format(self.toro2_homedir, config_file_name)
        except AttributeError as e:
            cfile_path = "{}/{}".format(TORO2_HOMEDIR, config_file_name)

        try:
            with open(cfile_path, 'r') as config:
                for cline in config.readlines():
                    li = cline.strip()
                    if li.startswith("#"):
                        continue
                    data = li.split("=")
                    config_dict[data[0]] = data[1]
        except Exception as e:
            print("[-] Unable to read config from {}: {}".format(cfile_path, e))

        return config_dict

    def write_config_file(self, config_file_name):
        if config_file_name is None:
            config_file_name = self.config_file_name

        try:
            cfile_path = "{}/{}".format(self.toro2_homedir, config_file_name)
        except AttributeError as e:
            cfile_path = "{}/{}".format(TORO2_HOMEDIR, config_file_name)

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
        elif sys.argv[1] == "integrate":
            toro2.os_fully_integrate()
        elif sys.argv[1] == "install":
            toro2.install()
        elif sys.argv[1] == "installnobackup":
            toro2.install(backup_osfiles=False)
        elif sys.argv[1] == "uninstall":
            toro2.uninstall()
            del toro2

        else:
            print("[-] Unknown '{}'.".format(sys.argv[1]))
    else:
        print("Usage: toro2 stop|switch|start|integrate|install|installnobackup|uninstall")
