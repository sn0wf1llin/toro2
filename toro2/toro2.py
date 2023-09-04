import shutil
import grp
import ast
import re
import os
import csv
import pwd
import sys
import subprocess
import signal
from functools import reduce


def is_process_up(pname):
    try:
        call = subprocess.check_output("pidof '{}'".format(pname), shell=True)
        return True
    except subprocess.CalledProcessError:
        return False


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


def get_os_release():
    release = {}
    with open('/etc/os-release') as f:
        reader = csv.reader(f, delimiter="=")
        for row in reader:
            if row:
                release[row[0]] = row[1]

    return release


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


def check_already_installed(f):
    def wrapper(*args, **kwargs):
        try:
            if not (os.path.isdir(args[0].toro2_homedir)
                    or os.path.exists(args[0].toro2_binary)) and f.__name__ != 'install':
                # print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] {args[0].toro2_binary} (or)
                # {args[0].toro2_homedir} not found. TORO2 not installed.')
                return None
        except Exception as e:
            print(f'[{bgcolors.LIGHT_RED_COLOR}X{bgcolors.RESET_COLOR}] {e}')
            return None

        return f(*args, **kwargs)

    return wrapper


def is_immutable(f):
    p = subprocess.Popen(['lsattr', f], bufsize=1, stdout=subprocess.PIPE)
    data, _ = p.communicate()
    return 'i' in data.decode('utf-8')


class Toro2:
    def __init__(self, config_file_name="toro2.conf"):
        # Var to store if naked() func used before
        # to manage files responsible for anonymity etc

        self._version = "2.4.2"
        self.version = f'TorO2 {self._version}\t10 Oct 2022'

        self.config_file_name = config_file_name
        self.files_to_backup = list(map(lambda i: i.format(os.getenv("HOME")),
                                        list(filter(os.path.exists, ["{}/.tor", "{}/.bashrc",
                                                                     "{}/.bashf", "{}/.bash_profile",
                                                                     "/etc/dnscrypt-proxy/dnscrypt-proxy.toml",
                                                                     "/etc/privoxy/config", "/etc/proxychains.conf",
                                                                     "/etc/dnsmasq.conf"]))))
        default_config = {
            "toro2_homedir":        "/etc/toro2",
            "toro2_path":           "/etc",
            "toro2_binary":         "/usr/bin/toro2",
            "backup_osfiles":       False,
            "tor_libdir":           None,
            "tor_logdir":           "/var/log/tor",
            "required_services":    ["privoxy", "dnscrypt-proxy"],
            "tor_as_process":       True,
            "tor_user":             "toro2",
            "iptables":             "/usr/bin/iptables",
            "iptables_save":        "/usr/bin/iptables-save",
            "iptables_restore":     "/usr/bin/iptables-restore",
            "ip6tables":            "/usr/bin/ip6tables",
            "ip6tables_save":       "/usr/bin/ip6tables-save",
            "ip6tables_restore":    "/usr/bin/ip6tables-restore",
            "systemctl":            "/usr/bin/systemctl",
            "chattr":               "/usr/bin/chattr",
            "username":             "toro2",
            "pidfile":              "/tmp/toro2.pid",
            "python3":              "/usr/bin/python3",
            "tor":                  "/usr/bin/tor",
            "dnscrypt_proxy_port":  5353,
            "tor_trans_port":       9040
        }

        self.config = default_config
        self.configure()

        # If tor_as_process = True and (!) tor in required_services => tor_as_process has higher priority
        if self.tor_as_process and 'tor' in [i.lower() for i in self.required_services]:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Not allowed: '
                  f'tor_as_process "{self.tor_as_process}" and "tor" in required_services "{self.required_servcies}"\n'
                  f'[{bgcolors.LIGHT_CYAN_COLOR}*{bgcolors.RESET_COLOR}] "tor" will be removed from required_services')
            self.required_services = list(set([i.lower() for i in self.required_services]))
            self.required_services.remove('tor')

        self.ipv4_lockfile = "{}/iptables.superbak.lock".format(self.toro2_homedir)
        self.ipv6_lockfile = "{}/ip6tables.superbak.lock".format(self.toro2_homedir)
        self.ipv4_bakfile = "{}/iptables.superbak".format(self.toro2_homedir)
        self.ipv6_bakfile = "{}/ip6tables.superbak".format(self.toro2_homedir)

        self.iamnaked = None

        if self.backup_osfiles:
            self.backup_curr_configs = self.backup_curr_configs_dummy
        else:
            self.backup_curr_configs = self._backup_curr_configs

        try:
            int(subprocess.getoutput("id -u {}".format(self.username)))
        except Exception as e:
            # print(f'[{bgcolors.LIGHT_RED_COLOR}X{bgcolors.RESET_COLOR}] {e}')
            self.user_op("toro2", "create")

    def help(self):
        print("""
    Usage: toro2 [start | stop | switch | naked | isnaked | install | uninstall | status | installnobackup | version]
            start                Start toro2 app (required to have it installed first)
            stop                 Stop toro2 app (stop services & tor)
            switch               Switch tor identity
            naked                Disables TorO2 protection until next start
            isnaked              Checks protection disabled
            install              Install toro2 app & files
            uninstall            Uninstall toro2 app & files
            status               Get state of tor & services
            installnobackup      Same as INSTALL, with no backup system files
            version              Print TorO2 version and exits
        """)

    def user_op(self, username, action):
        if action == "check":
            try:
                pwd.getpwnam(username)
                return True
            except KeyError:
                return False

        elif action == "create":
            if not self.user_op(username, "check"):
                self.username = username
                subprocess.run(['useradd', '--system', '--shell', '/bin/false', '--no-create-home', f'{username}'],
                               capture_output=False, shell=False, cwd=None, timeout=3)
                self.uid = int(subprocess.getoutput("id -u {}".format(self.username)))
                self.gid = int(subprocess.getoutput("id -g {}".format(self.username)))

        elif action == "delete":
            if self.user_op(username, "check"):
                subprocess.run(['userdel', f'{username}'], capture_output=False, shell=False, cwd=None, timeout=3)
                try:
                    grp.getgrnam(username)
                    subprocess.run(['groupdel', f'{username}'], capture_output=False,
                                   shell=False, cwd=None, timeout=3).check_returncode()
                except KeyError:
                    pass
                except subprocess.CalledProcessError as e:
                    print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR} to '
                          f'delete group {username} {bgcolors.RESET_COLOR}: CalledProcessError [{e}] ... ')
                except Exception as e:
                    print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR} to '
                          f'delete group {username} {bgcolors.RESET_COLOR}: [{e}] ... ')

            self.username = None

        elif action == "getuid":
            if self.user_op(username, "check"):
                return int(subprocess.getoutput("id -u {}".format(self.username)))
            return None

        elif action == "getgid":
            try:
                return int(subprocess.getoutput("id -g {}".format(self.username)))
            except Exception as e:
                return None

    def _read_config_file(self):
        config_dict = {}
        if os.path.exists(f'{self.toro2_homedir}'):
            conf = f'{self.toro2_homedir}/toro2/{self.config_file_name}'
        else:
            conf = f'{os.getcwd()}/toro2/{self.config_file_name}'

        if list(filter(os.path.exists, [conf])):
            with open(conf, 'r') as config:
                for cline in config.readlines():
                    li = cline.strip()
                    if li.startswith("#") or len(li) == 0:
                        continue
                    data = li.split("=")
                    val = data[1]
                    if '[' in val:
                        val = ast.literal_eval(val.strip())
                    config_dict[data[0]] = val

            print(f'[{bgcolors.LIGHT_GREEN_COLOR}+{bgcolors.RESET_COLOR}] Read config from {conf}')
        else:
            print(f'[{bgcolors.YELLOW_COLOR}.{bgcolors.RESET_COLOR}] Config not found ({conf})')

        return config_dict

    def configure(self):
        if self.config:
            for k, v in self.config.items():
                setattr(self, k, v)

        self._configure_tor()

        if self.config_file_name:
            rc = self._read_config_file()

            # for k, v in rc.items():
            #     self.config[k] = v
            self.config.update(rc)
            for k, v in self.config.items():
                setattr(self, k, v)

    @check_already_installed
    def _configure_tor(self):
        torrc_file = f'{self.toro2_homedir}/toro2/toro2.torrc'

        try:
            torrc = open(torrc_file, 'r')
        except Exception as e:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}.{bgcolors.RESET_COLOR}] Unable '
                  f'to read config from {torrc_file}: {e}')
            return
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

    def banner(self):
        banner = f'''

    --------[ version {self._version}        hh15461 ]--------
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

        '''
        print(banner)

    @staticmethod
    def backup_curr_configs_dummy():
        print(
            f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] {bgcolors.LIGHT_YELLOW_COLOR}Attention'
            f'{bgcolors.RESET_COLOR}: no backup for system files')

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
            subprocess.run(['mkdir', '-p', f'{backup_dir}'], capture_output=False, shell=False, cwd=None, timeout=3)
            os.chown(backup_dir, self.uid, self.gid)
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
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Trouble with'
                  f' makedir {"{}/{}".format(backup_dir, curr_backup_dir)}')

        os.chown("{}/{}".format(backup_dir, curr_backup_dir), self.uid, self.gid)

        for item in self.files_to_backup:
            if os.path.isdir(item):
                dir_name = item.split('/')[-1]
                copytree(item, "{}/{}/{}".format(backup_dir, curr_backup_dir, dir_name))
            else:
                shutil.copy2(item, "{}/{}/".format(backup_dir, curr_backup_dir))

        command4 = [f'{self.iptables_save}', '-f', f'{backup_dir}/{curr_backup_dir}/iptables.bak']
        command6 = [f'{self.ip6tables_save}', '-f', f'{backup_dir}/{curr_backup_dir}/ip6tables.bak']

        try:
            subprocess.run([command4], capture_output=False, shell=False, cwd=None, timeout=3).check_returncode()
            subprocess.run([command6], capture_output=False, shell=False, cwd=None, timeout=3).check_returncode()

        except subprocess.CalledProcessError as e:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR} to '
                  f'backup iptables {bgcolors.RESET_COLOR}: CalledProcessError [{e}] ... ')

        except Exception as e:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR} to '
                  f'backup iptables {bgcolors.RESET_COLOR}: [{e}] ... ')

    def _iptables_save(self):
        ipv4_save, ipv6_save = False, False
        try:
            # if iptables.superbak.lock & ip6tables.superbak.lock files exist AND
            # contains 1 => iptables were saved BEFORE
            # they changed via TORO2-rules, so, no need to save those ones

            if os.path.exists(self.ipv4_lockfile):
                with open(f'{self.ipv4_lockfile}', 'r') as f:
                    if int(f.read()) == 1:
                        print(f'[{bgcolors.LIGHT_YELLOW_COLOR}.{bgcolors.RESET_COLOR}] Already saved: iptables')
                    else:
                        ipv4_save = True
            else:
                ipv4_save = True

            if os.path.exists(self.ipv6_lockfile):
                with open(f'{self.ipv6_lockfile}', 'r') as f:
                    if int(f.read()) == 1:
                        print(f'[{bgcolors.LIGHT_YELLOW_COLOR}.{bgcolors.RESET_COLOR}] Already saved: ip6tables')
                    else:
                        ipv6_save = True
            else:
                ipv6_save = True

            if ipv4_save:
                subprocess.run([f'{self.iptables_save}', '-f', f'{self.ipv4_bakfile}'],
                               capture_output=False, shell=False, cwd=None, timeout=3)
                with open(f'{self.ipv4_lockfile}', 'w') as f:
                    f.write('1')

            if ipv6_save:
                subprocess.run([f'{self.ip6tables_save}', '-f', f'{self.ipv6_bakfile}'],
                               capture_output=False, shell=False, cwd=None, timeout=3)
                with open(f'{self.ipv6_lockfile}', 'w') as f:
                    f.write('1')

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to save iptables & ip6tables : {e}')

    def _iptables_restore(self):
        ipv4_restore, ipv6_restore = False, False

        try:
            if os.path.exists(self.ipv4_lockfile):
                with open(f'{self.ipv4_lockfile}', 'r') as f:
                    if int(f.read()) == 1:
                        ipv4_restore = True
                    else:
                        print(f'[{bgcolors.LIGHT_YELLOW_COLOR}.{bgcolors.RESET_COLOR}] Already restored: iptables')
            else:
                print(
                    f'[{bgcolors.LIGHT_YELLOW_COLOR}.{bgcolors.RESET_COLOR}] Not saved so can\'t be restored: iptables')

            if os.path.exists(self.ipv6_lockfile):
                with open(f'{self.ipv6_lockfile}', 'r') as f:
                    if int(f.read()) == 1:
                        ipv6_restore = True
                    else:
                        print(f'[{bgcolors.LIGHT_YELLOW_COLOR}.{bgcolors.RESET_COLOR}] Already restored: ip6tables')
            else:
                print(
                    f'[{bgcolors.LIGHT_YELLOW_COLOR}.{bgcolors.RESET_COLOR}] Not saved so can\'t be restored: ip6tables')

            if ipv4_restore:
                subprocess.run([f'{self.iptables_restore}', f'{self.ipv4_bakfile}'],
                               capture_output=False, shell=False, cwd=None, timeout=3)
                with open(f'{self.ipv4_lockfile}', 'w') as f:
                    f.write('0')

            if ipv6_restore:
                subprocess.run([f'{self.ip6tables_restore}', f'{self.ipv6_bakfile}'],
                               capture_output=False, shell=False, cwd=None, timeout=3)
                with open(f'{self.ipv6_lockfile}', 'w') as f:
                    f.write('0')

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to restore iptables & ip6tables : {e}')

    def _install_dnscrypt_proxy(self):
        dnscrypt_toml_file = "etc/dnscrypt-proxy/dnscrypt-proxy.toml"

        # Save old .toml
        self.rm_cp_sysfile(sfile=f'/{dnscrypt_toml_file}', command='cp', dfile=f'/{dnscrypt_toml_file}.bak')
        self.rm_cp_sysfile(sfile=f'{os.getcwd()}/toro2/{dnscrypt_toml_file}', command='cp',
                           dfile=f'/{dnscrypt_toml_file}')

    def _install_privoxy(self):
        try:
            copytree('toro2/etc/privoxy/templates', '/etc/privoxy/templates')
            privoxy_files_list = ['etc/privoxy/default.action', 'etc/privoxy/default.filter',
                                  'etc/privoxy/match-all.action', 'etc/privoxy/regression-tests.action',
                                  'etc/privoxy/trust', 'etc/privoxy/user.action', 'etc/privoxy/user.filter',
                                  'etc/privoxy/config']
            for pf in privoxy_files_list:
                self.rm_cp_sysfile(sfile=f'{os.getcwd()}/toro2/{pf}', command='cp', dfile=f'/{pf}')

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] {e}')

    def _install_dnsmasq(self):
        dnsm_conf = "etc/dnsmasq.conf"
        self.rm_cp_sysfile(sfile=f'{os.getcwd()}/toro2/{dnsm_conf}', command='cp', dfile=f'/{dnsm_conf}')

    def _manage_service(self, srv, action="status", sudo=False):
        command = [f'{self.systemctl}', f'{action}', f'{srv}']
        if sudo:
            command = ['sudo'] + command
        try:
            mng_p = subprocess.run(command, capture_output=False, shell=False, cwd=None, timeout=5,
                                   stdout=subprocess.DEVNULL)
            if action != 'status':
                mng_p.check_returncode()

            return True

        except subprocess.CalledProcessError as e:
            print(
                f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable to get "{bgcolors.CYAN_COLOR}{action}'
                f'{bgcolors.RESET_COLOR}" {srv}.service ... ')
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}.{bgcolors.RESET_COLOR}]: CalledProcessError [{e}]')

        except Exception as e:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable to get "{bgcolors.CYAN_COLOR}{action}'
                  f'{bgcolors.RESET_COLOR}" {srv}.service ... ')

            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}.{bgcolors.RESET_COLOR}]: [{e}]')
        finally:
            return False

    @check_already_installed
    def install(self, backup_osfiles_ultimate=True):
        print(f'[{bgcolors.LIGHT_BLUE_COLOR}.{bgcolors.RESET_COLOR}] Installing ... ')

        self.banner()

        if not os.path.isdir(self.toro2_homedir):
            os.makedirs(self.toro2_homedir)

        # backup iptables once when installing
        self._iptables_save()
        src = os.getcwd()
        dst = self.toro2_homedir

        if backup_osfiles_ultimate:
            self.config["backup_osfiles"] = backup_osfiles_ultimate
            self._write_config_file(self.config_file_name)
            self.configure()

        print(f'[{bgcolors.LIGHT_GRAY_COLOR}.{bgcolors.RESET_COLOR}] Copying toro2 files ... ')
        excludes = ('.idea', '.python-version', '.git', 'toro2/etc', 'toro2/usr', '.gitignore', 'install.sh',
                    'README.md')
        copytree(src, dst, ignore=excludes)

        print(f'[{bgcolors.LIGHT_GRAY_COLOR}.{bgcolors.RESET_COLOR}] Configuring & Installing dependencies ... ')

        # call installing functions defined by serviced required
        for rs in self.required_services:
            try:
                serv_install_func = getattr(self, '_install_{}'.format(rs.replace('-', '_')))
                serv_install_func()
                self._manage_service(rs, "disable", sudo=True)

            except Exception as e:
                print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Can\'t install '
                      f'{bgcolors.LIGHT_YELLOW_COLOR}{rs}{bgcolors.RESET_COLOR} : possible absence '
                      f'{bgcolors.LIGHT_MAGENTA_COLOR}{"_install_{}".format(rs.replace("-", "_"))}'
                      f'{bgcolors.RESET_COLOR} installation function : {e}')

        print(f'[{bgcolors.LIGHT_GRAY_COLOR}.{bgcolors.RESET_COLOR}] '
              f'{"{}/toro2/etc/proxychains.conf".format(os.getcwd())} to /etc/proxychains.conf ... ')
        shutil.copy("{}/toro2/etc/proxychains.conf".format(os.getcwd()), '/etc/proxychains.conf')

        print(f'[{bgcolors.LIGHT_GRAY_COLOR}.{bgcolors.RESET_COLOR}] '
              f'{"{}/toro2/toro2".format(os.getcwd())} to {self.toro2_binary} ... ')
        shutil.copy("{}/toro2/toro2".format(os.getcwd()), self.toro2_binary)
        os.chmod(self.toro2_binary, 0o755)

        try:
            os.chown(self.toro2_homedir, self.user_op(self.username, 'getuid'), self.user_op(self.username, 'getgid'))

        except Exception as e:
            print(
                f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to set attrs for {self.toro2_homedir}: {e}')

        print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Successfully installed to {dst}')
        print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Executable: {self.toro2_binary}')

    @check_already_installed
    def uninstall(self):
        print(f'[{bgcolors.LIGHT_BLUE_COLOR}.{bgcolors.RESET_COLOR}] Uninstalling ... ')

        if self.status() == 0:
            self.stop()

        self.aminaked()
        if not self.iamnaked:
            self.naked()

        try:
            try:
                shutil.rmtree(self.toro2_homedir)
                print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Remove {self.toro2_homedir} ... ')

                if os.path.isdir(f'{self.toro2_stuff_homedir}'):
                    shutil.rmtree(self.toro2_stuff_homedir)
                    print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Remove {self.toro2_stuff_homedir} ... ')

            except Exception as e:
                print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] {e}')

            if os.path.isfile(self.toro2_binary):
                os.remove(self.toro2_binary)
                print(f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] Executable {self.toro2_binary} removed')

            self.user_op(self.username, "delete")

        except FileNotFoundError as e:
            print(f'[{bgcolors.LIGHT_CYAN_COLOR}+/-{bgcolors.RESET_COLOR}] toro2 not installed\n{e}')

        except Exception as e:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] {e}')

    def kill_tor(self):
        # check toro2.torrc for tor mode
        # if RunAsDaemon 1 then stop tor.service
        # else kill tor process

        if self.tor_as_process:
            try:
                subprocess.run(['sudo', 'killall', 'tor'], capture_output=False, timeout=3,
                               shell=False).check_returncode()
            except subprocess.CalledProcessError as e:
                print(
                    f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR}killall'
                    f'{bgcolors.RESET_COLOR} tor: CalledProcessError [{e}] ... ')
            except Exception as e:
                print(
                    f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR}killall'
                    f'{bgcolors.RESET_COLOR} tor: Unknown exception [{e}] ... ')

        else:
            self._manage_service("tor", "stop", sudo=True)

    def iptablesA(self):
        print(f'[{bgcolors.LIGHT_BLUE_COLOR}.{bgcolors.RESET_COLOR}] Adding rules ... ')

        bad_ifaces = ['lo']
        # out_ifaces = "".join(i + " " for i in os.listdir('/sys/class/net') if i not in bad_ifaces)[:-1]
        try:
            subprocess.run(['sudo', f'{self.toro2_homedir}/toro2/toro2.iptablesA']).check_returncode()
        except subprocess.CalledProcessError as e:
            print(
                f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR} '
                f'to set TorO2 iptables rules {bgcolors.RESET_COLOR}: CalledProcessError [{e}] ... ')

    def iptablesD(self):
        print(f'[{bgcolors.LIGHT_BLUE_COLOR}.{bgcolors.RESET_COLOR}] Deleting rules ... ')

        try:
            subprocess.run(['sudo', f'{self.toro2_homedir}/toro2/toro2.iptablesD']).check_returncode()
        except subprocess.CalledProcessError as e:
            print(
                f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR} '
                f'{bgcolors.RESET_COLOR} to remove TorO2 iptables rules: CalledProcessError [{e}] ... ')

    def rm_cp_sysfile(self, sfile, command, dfile=None):
        if os.path.exists(sfile):
            if command == 'rm':
                query = ['sudo', f'{command}', '-f', f'{sfile}']
            elif command == 'cp':
                if dfile is None:
                    dfile = "/{}".format(sfile)

                query = ['sudo', f'{command}', '-f', f'{sfile}', f'{dfile}']

            try:
                subprocess.run(query, capture_output=False,
                               timeout=3, shell=False).check_returncode()
            except subprocess.CalledProcessError as e:
                print(
                    f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unable {bgcolors.CYAN_COLOR} '
                    f'{bgcolors.RESET_COLOR} to {command} "{sfile}": CalledProcessError [{e}] ... ')

    def manage_srvpack(self, srvpack, command, chkcommand=['is-active', '--quiet'], chkcommand_true=0):
        managed = {}
        if isinstance(srvpack, dict):
            srvpack = [i for i in srvpack.keys()]

        for rserv in srvpack:
            rserv_process = self._manage_service(rserv, command, sudo=True)

            if chkcommand is None:
                managed[rserv] = rserv_process
            else:
                if not isinstance(chkcommand, list):
                    chkcommand = [chkcommand]

                rserv_status = subprocess.Popen(['sudo', f'{self.systemctl}', *chkcommand, f'{rserv}'],
                                                stdout=subprocess.DEVNULL)
                rserv_status.communicate()
                managed[rserv] = rserv_status.returncode == chkcommand_true

        for sn, sc in managed.items():
            clr, lbl = bgcolors.RED_COLOR, '-'
            if sc:
                clr, lbl = bgcolors.GREEN_COLOR, '+'

            print(f'[{clr}{lbl}{bgcolors.RESET_COLOR}] {command} {bgcolors.WHITE_COLOR}{sn}{bgcolors.RESET_COLOR}')

        return managed, reduce(lambda x, y: x & y, managed.values())

    @check_already_installed
    def version(self):
        return self.version

    @check_already_installed
    def start(self):
        print(f'[{bgcolors.LIGHT_BLUE_COLOR}.{bgcolors.RESET_COLOR}] Starting ... ')

        self.aminaked()

        if self.iamnaked:
            # naked() previously used!
            # files-anonymity providers must be restored!
            # /etc/resolv.conf for now
            try:
                subprocess.run([f'{self.chattr}', '-i', '/etc/resolv.conf'], capture_output=False,
                               timeout=3, shell=False).check_returncode()
                with open("/etc/resolv.conf", 'w') as f:
                    f.write("nameserver ::1\nnameserver 127.0.0.1\noptions edns0 single-request-reopen")

                subprocess.run([f'{self.chattr}', '+i', '/etc/resolv.conf'], capture_output=False,
                               timeout=3, shell=False).check_returncode()
                self.iamnaked = False

            except subprocess.CalledProcessError as e:
                print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to hide your ass, dude. '
                      f'CalledProcessError [{e}]')

            except Exception as e:
                print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to hide your ass, dude. [{e}]')

        # def set_environment_proxies():
        #     for sp in ['ftp_proxy', 'https_proxy', 'telnet_proxy', 'http_proxy']:
        #         os.environ[sp] = PRIVOXY_ADDR
        #         os.environ[sp.upper()] = PRIVOXY_ADDR
        # set_environment_proxies()

        if not os.path.exists(self.pidfile):
            with open(self.pidfile, 'w') as f:
                f.write(str(os.getpid()))

            # self.backup_curr_configs()
            self.iptablesA()

            # print(
            #     f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] '
            #     f'{bgcolors.WHITE_COLOR}iptables{bgcolors.RESET_COLOR}: '
            #     f'{bgcolors.GREEN_COLOR}add{bgcolors.RESET_COLOR} new rules')

            managed, mng_retcode = self.manage_srvpack(srvpack=self.required_services, command="start",
                                                       chkcommand=['is-active', '--quiet'], chkcommand_true=0)

            if mng_retcode:
                if self.tor_as_process:
                    print(
                        f'[{bgcolors.GREEN_COLOR}+{bgcolors.RESET_COLOR}] '
                        f'Starting {bgcolors.WHITE_COLOR}tor{bgcolors.RESET_COLOR} ... ')

                    try:
                        subprocess.run(['sudo', f'{self.tor_bin}', '-f',
                                        f'{self.toro2_homedir}/toro2/toro2.torrc']).check_returncode()

                    except KeyboardInterrupt:
                        self.stop(kill_tor=False)
                        exit(0)

                    except subprocess.CalledProcessError as e:
                        print(f'[{bgcolors.LIGHT_RED_COLOR}x{bgcolors.RESET_COLOR}] '
                              f'Unable to start tor: CalledProcessError [{e}]')
                        self.stop(kill_tor=False)
                        exit(-1)

                    except Exception as e:
                        print(f'[{bgcolors.LIGHT_RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to start tor: [{e}]')
                        self.stop()
                        exit(-1)
                else:
                    # tor is run as service
                    self._manage_service("tor", "start", sudo=True)

            else:
                # something happened => stop those services which are already started
                stopped, stop_retcode = self.manage_srvpack(srvpack=managed, command="stop",
                                                            chkcommand=['is-active', '--quiet'], chkcommand_true=3)
                self.rm_cp_sysfile(sfile=self.pidfile, command='rm')
                exit(1)
        else:
            pid = None
            with open(self.pidfile, 'r') as f:
                pid = f.readline().strip()

            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] TorO2 already started with PID '
                  f'{bgcolors.LIGHT_YELLOW_COLOR} {pid} {bgcolors.RESET_COLOR}')

    @check_already_installed
    def stop(self, kill_tor=True):
        print(f'[{bgcolors.LIGHT_BLUE_COLOR}.{bgcolors.RESET_COLOR}] Stopping ... ')

        self.rm_cp_sysfile(sfile=self.pidfile, command='rm')

        if kill_tor:
            self.kill_tor()

        self.rm_cp_sysfile(sfile=self.ipv4_lockfile, command='rm')

        self.rm_cp_sysfile(sfile=self.ipv6_lockfile, command='rm')

        self.iptablesD()

        managed, mng_retcode = self.manage_srvpack(srvpack=self.required_services, command="stop",
                                                   chkcommand=['is-active', '--quiet'], chkcommand_true=3)

        if mng_retcode:
            print(f'[{bgcolors.LIGHT_GREEN_COLOR}+{bgcolors.RESET_COLOR}] '
                  f'{bgcolors.WHITE_COLOR}Stopped.{bgcolors.RESET_COLOR}')
        else:
            # print(f'[{bgcolors.LIGHT_MAGENTA_COLOR}*{bgcolors.RESET_COLOR}] '
            #       f'[{bgcolors.MAGENTA_COLOR}DEBUG{bgcolors.RESET_COLOR}] {managed}')
            print(f'[{bgcolors.LIGHT_RED_COLOR}x{bgcolors.RESET_COLOR}] '
                  f'{bgcolors.WHITE_COLOR}Unable to stop.{bgcolors.RESET_COLOR}')

    @check_already_installed
    def status(self):
        # curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/
        all_status = {}

        if not self.tor_as_process:
            rservices = self.required_services + ["tor"]
        else:
            all_status['tor'] = is_process_up('tor')
            rservices = self.required_services
            tor_status = subprocess.getoutput("ps -fC tor | tail -n 1 | grep -v PPID || echo 'no info'")
            clr, lbl = bgcolors.RED_COLOR, '-'
            if tor_status != 'no info':
                clr, lbl = bgcolors.LIGHT_GREEN_COLOR, '+'

            print(f'[{clr}{lbl}{bgcolors.RESET_COLOR}] Tor')

        managed, mng_retcode = self.manage_srvpack(srvpack=rservices, command="status",
                                                   chkcommand=['is-active', '--quiet'], chkcommand_true=0)

        # print(f'[{bgcolors.LIGHT_MAGENTA_COLOR}*{bgcolors.RESET_COLOR}] '
        #       f'[{bgcolors.MAGENTA_COLOR}DEBUG{bgcolors.RESET_COLOR}] {managed} code: {mng_retcode}')

        return mng_retcode

    def aminaked(self):
        p = ['REJECT', 'DROP']
        iptables_policy_string = subprocess.Popen(['sudo', f'{self.iptables}', '-L', 'OUTPUT', '-n'],
                                                  stdout=subprocess.PIPE).communicate()[0].decode("utf-8")

        ip6tables_policy_string = subprocess.Popen(['sudo', f'{self.ip6tables}', '-L', 'OUTPUT', '-n'],
                                                   stdout=subprocess.PIPE).communicate()[0].decode("utf-8")

        if ip6tables_policy_string and iptables_policy_string:
            ipp = re.findall(r'\(policy.*\)', iptables_policy_string)
            ip6p = re.findall(r'\(policy.*\)', ip6tables_policy_string)
            self.iamnaked = (ipp[0].split(' ')[1][:-1] not in p) or (ip6p[0].split(' ')[1][:-1] not in p) or (not is_immutable("/etc/resolv.conf"))

    def naked(self):
        if self.status():
            self.stop()

        self.iamnaked = True

        try:
            subprocess.run(['sudo', f'{self.iptables}', '-P', 'OUTPUT', 'ACCEPT'],
                           capture_output=False, timeout=3, shell=False).check_returncode()
        except subprocess.CalledProcessError as e:
            self.iamnaked = False
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to set policy ACCEPT: {e}')

        try:
            subprocess.run(['sudo', f'{self.chattr}', '-i', '/etc/resolv.conf'],
                           capture_output=False, timeout=3, shell=False).check_returncode()
            with open("/etc/resolv.conf", 'w') as f:
                f.write(f'nameserver {self.naked_nameserver}')

        except subprocess.CalledProcessError as e:
            self.iamnaked = False
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to chattr /etc/resolv.conf: {e}')

        if not self.iamnaked:
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to restore files to make you naked')

    @check_already_installed
    def switch_identity(self):
        print(f'[{bgcolors.LIGHT_BLUE_COLOR}.{bgcolors.RESET_COLOR}] Switching identity ... ')

        try:
            tor_pid = get_pid("tor")
            os.kill(tor_pid, signal.SIGHUP)

        except Exception as e:
            print(
                f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to kill {bgcolors.LIGHT_YELLOW_COLOR}Tor'
                f'{bgcolors.RESET_COLOR}: {e}')

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
            print(f'[{bgcolors.RED_COLOR}x{bgcolors.RESET_COLOR}] Unable to save config to {cfile_path}: {e}')


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

        elif sys.argv[1] == "install":
            toro2.install()

        # naked is for disabling iptables rules & restore /etc/resolv.conf to
        # give UNSAFE access to network IF YOU NEED IT NOW
        elif sys.argv[1] == "naked":
            toro2.naked()

        elif sys.argv[1] == "isnaked":
            toro2.aminaked()
            print(f'[{bgcolors.LIGHT_BLUE_COLOR}.{bgcolors.RESET_COLOR}] Naked: {toro2.iamnaked} ')

        elif sys.argv[1] == "installnobackup":
            toro2.install(backup_osfiles_ultimate=False)

        elif sys.argv[1] == "uninstall":
            toro2.uninstall()
            del toro2

        elif sys.argv[1] == "help":
            toro2.help()

        elif sys.argv[1] == "version":
            toro2.version()

        else:
            print(f'[{bgcolors.LIGHT_YELLOW_COLOR}-{bgcolors.RESET_COLOR}] Unknown command \'{sys.argv[1]}\'')
    else:
        toro2.help()
