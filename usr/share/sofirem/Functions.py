# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================

import os
import sys
import psutil
import time
import datetime
from datetime import datetime, timedelta
import subprocess
import threading  # noqa
import gi
import logging
from threading import Thread
from Package import Package
from distro import id
from os import makedirs

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa

# =====================================================
#               Base Directory
# =====================================================

base_dir = os.path.dirname(os.path.realpath(__file__))

# =====================================================
#               Global Variables
# =====================================================
sudo_username = os.getlogin()
home = "/home/" + str(sudo_username)
path_dir_cache = base_dir + "/cache/"
packages = []
debug = False
distr = id()

# this timeout is for the pacman sync, pacman lock file, install/uninstall processes
# 10m timeout
process_timeout = 600

arcolinux_mirrorlist = "/etc/pacman.d/arcolinux-mirrorlist"
pacman_conf = "/etc/pacman.conf"
pacman_logfile = "/var/log/pacman.log"
pacman_lockfile = "/var/lib/pacman/db.lck"

atestrepo = "#[arcolinux_repo_testing]\n\
#SigLevel = Optional TrustedOnly\n\
#Include = /etc/pacman.d/arcolinux-mirrorlist"

arepo = "[arcolinux_repo]\n\
SigLevel = Optional TrustedOnly\n\
Include = /etc/pacman.d/arcolinux-mirrorlist"

a3prepo = "[arcolinux_repo_3party]\n\
SigLevel = Optional TrustedOnly\n\
Include = /etc/pacman.d/arcolinux-mirrorlist"

axlrepo = "[arcolinux_repo_xlarge]\n\
SigLevel = Optional TrustedOnly\n\
Include = /etc/pacman.d/arcolinux-mirrorlist"

log_dir = "/var/log/sofirem/%s/" % datetime.now().strftime("%Y-%m-%d")
event_log_file = "%s/%s-event.log" % (
    log_dir,
    datetime.now().strftime("%H-%M-%S"),
)

# Create log directory and the event log file
try:
    if not os.path.exists(log_dir):
        makedirs(log_dir)

    print("[INFO] Log directory = %s" % log_dir)

except os.error as oe:
    print("[ERROR] Exception in setup log_directory: %s" % oe)
    sys.exit(1)

logger = logging.getLogger("logger")

logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

fh = logging.FileHandler(event_log_file, mode="a", encoding="utf-8", delay=False)
fh.setLevel(level=logging.DEBUG)

# create formatter
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s > %(message)s", "%Y-%m-%d %H:%M:%S"
)
# add formatter to ch
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

# add fh to logger
logger.addHandler(fh)


# get position in list
def get_position(lists, value):
    data = [string for string in lists if value in string]
    if len(data) != 0:
        position = lists.index(data[0])
        return position
    return 0


# a before state of packages
def create_packages_log():
    try:
        logger.info("Creating a list of currently installed packages")
        packages_log = "%s-packages.log" % datetime.now().strftime("%H-%M-%S")
        logger.info("Saving in %s" % packages_log)
        cmd = ["pacman", "-Q"]

        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            with open("%s/%s" % (log_dir, packages_log), "w") as f:
                for line in process.stdout:
                    f.write("%s" % line)
    except Exception as e:
        logger.error("Exception in create_packages_log(): %s" % e)


# =====================================================
#               GLOBAL FUNCTIONS
# =====================================================


def _get_position(lists, value):
    data = [string for string in lists if value in string]
    position = lists.index(data[0])
    return position


def is_file_stale(filepath, stale_days, stale_hours, stale_minutes):
    # first, lets obtain the datetime of the day that we determine data to be "stale"
    now = datetime.now()
    # For the purposes of this, we are assuming that one would have the app open longer than 5 minutes if installing.
    stale_datetime = now - timedelta(
        days=stale_days, hours=stale_hours, minutes=stale_minutes
    )
    # Check to see if the file path is in existence.
    if os.path.exists(filepath):
        # if the file exists, when was it made?
        file_created = datetime.fromtimestamp(os.path.getctime(filepath))
        # file is older than the time delta identified above
        if file_created < stale_datetime:
            return True
    return False


# =====================================================
#               PERMISSIONS
# =====================================================


def permissions(dst):
    try:
        groups = subprocess.run(
            ["sh", "-c", "id " + sudo_username],
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for x in groups.stdout.decode().split(" "):
            if "gid" in x:
                g = x.split("(")[1]
                group = g.replace(")", "").strip()
        subprocess.call(["chown", "-R", sudo_username + ":" + group, dst], shell=False)

    except Exception as e:
        logger.error(e)


# =====================================================
#               PACMAN SYNC PACKAGE DB
# =====================================================
def sync_package_db():
    try:
        sync_str = ["pacman", "-Sy"]
        logger.info("Synchronising package databases")
        process_sync = subprocess.run(
            sync_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
        )

        if process_sync.returncode == 0:
            return None
        else:
            if process_sync.stdout:
                out = str(process_sync.stdout.decode("utf-8"))
                logger.error(out)

                return out

    except Exception as e:
        logger.error("Exception in sync(): %s" % e)


def start_subprocess(self, cmd, progress_dialog, action, pkg, widget):
    try:
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            progress_dialog.pkg_dialog_closed = False
            self.in_progress = True
            widget.set_sensitive(False)

            line = "Pacman is processing the %s of package %s \n\n" % (action, pkg.name)

            GLib.idle_add(
                update_progress_textview,
                self,
                line,
                progress_dialog,
                # progress_dialog.package_progress_textview.get_buffer(),
                # progress_dialog.package_progress_textview,
                priority=GLib.PRIORITY_DEFAULT,
            )
            logger.debug("Waiting for pacman process, timeout = %s" % process_timeout)
            # process.wait(process_timeout)
            logger.debug("Pacman is now processing the request")
            while process.poll() is None:
                for line in process.stdout:
                    if progress_dialog.pkg_dialog_closed:
                        break
                    GLib.idle_add(
                        update_progress_textview,
                        self,
                        line,
                        progress_dialog,
                        # progress_dialog.package_progress_textview.get_buffer(),
                        # progress_dialog.package_progress_textview,
                        priority=GLib.PRIORITY_DEFAULT,
                    )

                    time.sleep(0.3)

            if process.returncode == 0:
                logger.info("Package %s = completed" % action)
                # time.sleep(0.2)
                GLib.idle_add(
                    toggle_switch,
                    self,
                    action,
                    widget,
                    pkg,
                    progress_dialog,
                    priority=GLib.PRIORITY_DEFAULT,
                )
                progress_dialog.btn_package_progress_close.set_sensitive(True)
                self.in_progress = False

            else:
                self.in_progress = False
                if action == "install":
                    logger.error("Package install = failed")

                if action == "uninstall":
                    logger.error("Package uninstall = failed")

                GLib.idle_add(
                    toggle_switch,
                    self,
                    action,
                    widget,
                    pkg,
                    progress_dialog,
                    priority=GLib.PRIORITY_DEFAULT,
                )

                progress_dialog.btn_package_progress_close.set_sensitive(True)

            # time.sleep(0.1)
    except TimeoutError as t:
        logger.error("TimeoutError in %s start_subprocess(): %s" % (action, t))
        process.terminate()
        progress_dialog.btn_package_progress_close.set_sensitive(True)
        # deactivate switch widget, install failed

    except SystemError as s:
        logger.error("SystemError in %s start_subprocess(): %s" % (action, s))
        process.terminate()
        progress_dialog.btn_package_progress_close.set_sensitive(True)
        # deactivate switch widget, install failed


def toggle_switch(self, action, switch, pkg, progress_dialog):
    logger.debug("Toggling switch state")
    installed = check_package_installed(pkg.name)
    if installed and action == "install":
        logger.debug("Toggle switch state = True")
        switch.set_state(True)
        # switch.set_active(True)
        switch.set_sensitive(True)
        progress_dialog.set_title("Package install for %s completed" % pkg.name)

        if progress_dialog.pkg_dialog_closed is False:
            progress_dialog.infobar.set_name("infobar_info")

            content = progress_dialog.infobar.get_content_area()
            if content is not None:
                for widget in content.get_children():
                    content.remove(widget)

                lbl_install = Gtk.Label(xalign=0, yalign=0)
                lbl_install.set_markup("<b>Package %s installed</b>" % pkg.name)

                content.add(lbl_install)

                if self.timeout_id is not None:
                    GLib.source_remove(self.timeout_id)
                    self.timeout_id = None

                self.timeout_id = GLib.timeout_add(
                    200, reveal_infobar, self, progress_dialog
                )

    if installed is False and action == "install":
        # install failed/terminated
        switch.set_state(False)
        switch.set_active(False)
        switch.set_sensitive(True)

        progress_dialog.set_title("Package install for %s failed" % pkg.name)

        if progress_dialog.pkg_dialog_closed is False:
            progress_dialog.infobar.set_name("infobar_error")

            content = progress_dialog.infobar.get_content_area()
            if content is not None:
                for widget in content.get_children():
                    content.remove(widget)

                lbl_install = Gtk.Label(xalign=0, yalign=0)
                lbl_install.set_markup("<b>Package %s install failed</b>" % pkg.name)

                content.add(lbl_install)

                if self.timeout_id is not None:
                    GLib.source_remove(self.timeout_id)
                    self.timeout_id = None

                self.timeout_id = GLib.timeout_add(
                    200, reveal_infobar, self, progress_dialog
                )

    if installed is False and action == "uninstall":
        logger.debug("Toggle switch state = False")
        switch.set_state(False)
        switch.set_active(False)
        switch.set_sensitive(True)
        progress_dialog.set_title("Package uninstall for %s completed" % pkg.name)

        if progress_dialog.pkg_dialog_closed is False:
            progress_dialog.infobar.set_name("infobar_info")
            content = progress_dialog.infobar.get_content_area()
            if content is not None:
                for widget in content.get_children():
                    content.remove(widget)

                lbl_install = Gtk.Label(xalign=0, yalign=0)
                lbl_install.set_markup("<b>Package %s uninstalled</b>" % pkg.name)

                content.add(lbl_install)

                if self.timeout_id is not None:
                    GLib.source_remove(self.timeout_id)
                    self.timeout_id = None

                self.timeout_id = GLib.timeout_add(
                    200, reveal_infobar, self, progress_dialog
                )

    if installed is True and action == "uninstall":
        # uninstall failed/terminated
        switch.set_state(True)
        switch.set_active(True)
        switch.set_sensitive(True)

        progress_dialog.set_title("Package uninstall for %s failed" % pkg.name)

        if progress_dialog.pkg_dialog_closed is False:
            progress_dialog.infobar.set_name("infobar_err")

            content = progress_dialog.infobar.get_content_area()
            if content is not None:
                for widget in content.get_children():
                    content.remove(widget)

                lbl_install = Gtk.Label(xalign=0, yalign=0)
                lbl_install.set_markup("<b>Package %s uninstall failed</b>" % pkg.name)

                content.add(lbl_install)

                if self.timeout_id is not None:
                    GLib.source_remove(self.timeout_id)
                    self.timeout_id = None

                self.timeout_id = GLib.timeout_add(
                    500, reveal_infobar, self, progress_dialog
                )


# def update_progress_textview(self, line, buffer, textview):
def update_progress_textview(self, line, progress_dialog):
    if progress_dialog.pkg_dialog_closed is False and self.in_progress is True:
        buffer = progress_dialog.package_progress_textview.get_buffer()
        if len(line) > 0 or buffer is None:
            buffer.insert(buffer.get_end_iter(), "  %s" % line, len("  %s" % line))

            text_mark_end = buffer.create_mark("\nend", buffer.get_end_iter(), False)

            progress_dialog.package_progress_textview.scroll_mark_onscreen(
                text_mark_end
            )
    else:
        logger.debug(
            "Package progress dialog closed/in progress = False, stop updating UI"
        )

        return False


# =====================================================
#               APP INSTALLATION
# =====================================================
def install(self):
    pkg, action, widget, inst_str, progress_dialog = self.pkg_queue.get()

    try:
        if action == "install":
            # path = base_dir + "/cache/installed.lst"
            logger.debug("Running inside install thread")

            logger.info("Installing package %s" % pkg.name)

            # create_package_progress_dialog(self, action, pkg, " ".join(inst_str))

            th_subprocess_install = Thread(
                name="thread_subprocess",
                target=start_subprocess,
                args=(
                    self,
                    inst_str,
                    progress_dialog,
                    action,
                    pkg,
                    widget,
                ),
                daemon=True,
            )

            th_subprocess_install.start()

            logger.debug("Thread: subprocess install started")

    except Exception as e:
        logger.error("Exception in install(): %s" % e)
        # deactivate switch widget, install failed
        widget.set_state(False)
        self.btn_package_progress_close.set_sensitive(True)
    finally:
        self.pkg_queue.task_done()


# =====================================================
#               APP UNINSTALLATION
# =====================================================
def uninstall(self):
    pkg, action, widget, uninst_str, progress_dialog = self.pkg_queue.get()

    try:
        if action == "uninstall":
            # path = base_dir + "/cache/installed.lst"
            logger.debug("Running inside uninstall thread")
            logger.info("Removing package %s" % pkg.name)

            # get pacman process currently running, is the package which is requested
            # to be uninstalled currently being installed ?

            # proc = get_pacman_process()

            # create_package_progress_dialog(self, action, pkg, " ".join(uninst_str))

            th_subprocess_uninstall = Thread(
                name="thread_subprocess",
                target=start_subprocess,
                args=(
                    self,
                    uninst_str,
                    progress_dialog,
                    action,
                    pkg,
                    widget,
                ),
                daemon=True,
            )

            th_subprocess_uninstall.start()

            logger.debug("Thread: subprocess uninstall started")

    except Exception as e:
        widget.set_state(True)
        progress_dialog.btn_package_progress_close.set_sensitive(True)
        logger.error("Exception in uninstall(): %s" % e)
    finally:
        # Now check uninstall_state for any packages which failed to uninstall
        # display dependencies notification to user here
        logger.debug("Checking if package %s is installed" % pkg.name)
        if check_package_installed(pkg.name) is True:
            logger.debug("Package is installed")
            widget.set_state(True)
        else:
            logger.debug("Package is not installed")
            widget.set_state(False)
        self.pkg_queue.task_done()


# =====================================================
#               SEARCH INDEXING
# =====================================================


# store a list of package metadata into memory for fast retrieval
def store_packages():
    path = base_dir + "/yaml/"
    yaml_files = []
    packages = []

    category_dict = {}

    try:
        # get package version info
        version_info_lst = getPackageVersion()

        # get a list of yaml files
        for file in os.listdir(path):
            if file.endswith(".yaml"):
                yaml_files.append(file)

        if len(yaml_files) > 0:
            for yaml_file in yaml_files:
                cat_desc = ""
                package_name = ""
                package_cat = ""

                category_name = yaml_file[11:-5].strip().capitalize()

                # read contents of each yaml file

                with open(path + yaml_file, "r") as yaml:
                    content = yaml.readlines()
                for line in content:
                    if line.startswith("  packages:"):
                        continue
                    elif line.startswith("  description: "):
                        # Set the label text for the description line
                        subcat_desc = (
                            line.strip("  description: ")
                            .strip()
                            .strip('"')
                            .strip("\n")
                            .strip()
                        )
                    elif line.startswith("- name:"):
                        # category

                        subcat_name = (
                            line.strip("- name: ")
                            .strip()
                            .strip('"')
                            .strip("\n")
                            .strip()
                        )
                    elif line.startswith("    - "):
                        # add the package to the packages list

                        package_name = line.strip("    - ").strip()
                        # get the package description
                        package_desc = obtain_pkg_description(package_name)

                        # get the package version, lookup dictionary

                        package_version = "unknown"

                        for i in version_info_lst:
                            for name, version in i.items():
                                if name == package_name:
                                    package_version = version
                                    continue

                        package = Package(
                            package_name,
                            package_desc,
                            category_name,
                            subcat_name,
                            subcat_desc,
                            package_version,
                        )

                        packages.append(package)

        # filter the results so that each category holds a list of package

        category_name = None
        packages_cat_lst = []
        for pkg in packages:
            if category_name == pkg.category:
                packages_cat_lst.append(pkg)
                category_dict[category_name] = packages_cat_lst
            elif category_name is None:
                packages_cat_lst.append(pkg)
                category_dict[pkg.category] = packages_cat_lst
            else:
                # reset packages, new category
                packages_cat_lst = []

                packages_cat_lst.append(pkg)

                category_dict[pkg.category] = packages_cat_lst

            category_name = pkg.category

        """
        Print dictionary for debugging

        for key in category_dict.keys():
            print("Category = %s" % key)
            pkg_list = category_dict[key]

            for pkg in pkg_list:
                print(pkg.name)
                #print(pkg.category)


            print("++++++++++++++++++++++++++++++")
        """

        sorted_dict = None

        sorted_dict = dict(sorted(category_dict.items()))

        return sorted_dict
    except Exception as e:
        print("Exception in storePackages() : %s" % e)
        sys.exit(1)


# =====================================================
#              PACKAGE VERSIONS
# =====================================================


# get live package version info
def getPackageVersion():
    query_str = ["pacman", "-Si"]

    try:
        process_pkg_query = subprocess.Popen(
            query_str, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        out, err = process_pkg_query.communicate(timeout=process_timeout)

        if process_pkg_query.returncode == 0:
            if out:
                package_data = []
                pkg_name = None
                for line in out.decode("utf-8").splitlines():
                    package_dict = {}
                    if "Name            :" in line.strip():
                        pkg_name = line.replace(" ", "").split("Name:")[1]
                    if "Version         :" in line.strip():
                        pkg_version = line.replace(" ", "").split("Version:")[1]
                        package_dict[pkg_name] = pkg_version

                        package_data.append(package_dict)

                return package_data
        else:
            logger.error("Failed to extract package version information.")

    except Exception as e:
        logger.error("Exception in getPackageVersion() : %s" % e)


# get installed package version, installed date, name to be displayed inside the treeview
# when the show packages button is clicked on


def get_installed_package_data():
    query_str = ["pacman", "-Qi"]

    try:
        installed_packages_lst = []
        pkg_name = None
        pkg_version = None
        pkg_install_date = None
        pkg_installed_size = None

        with subprocess.Popen(
            query_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            for line in process.stdout:
                if "Name            :" in line.strip():
                    pkg_name = line.replace(" ", "").split("Name:")[1].strip()

                if "Version         :" in line.strip():
                    pkg_version = line.replace(" ", "").split("Version:")[1].strip()

                if "Installed Size  :" in line.strip():
                    pkg_installed_size = line.split("Installed Size  :")[1].strip()

                if "Install Date    :" in line.strip():
                    pkg_install_date = line.split("Install Date    :")[1].strip()

                    installed_packages_lst.append(
                        (pkg_name, pkg_version, pkg_install_date, pkg_installed_size)
                    )

        return installed_packages_lst

    except Exception as e:
        logger.error("Exception in get_installed_package_data() : %s" % e)


# get key package information which is to be shown inside the progress dialog window switcher
# this is called for packages which are not yet installed
def get_package_information(self, package_name):
    logger.info("Fetching package information for %s" % package_name)
    query_str = ["pacman", "-Sii", package_name]
    try:
        pkg_name = None
        pkg_version = None
        pkg_repository = None
        pkg_description = None
        pkg_arch = None
        pkg_url = None
        pkg_depends_on = []
        pkg_conflicts_with = []
        pkg_download_size = None
        pkg_installed_size = None
        pkg_build_date = None
        pkg_packager = None

        with subprocess.Popen(
            query_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            for line in process.stdout:
                if "Name            :" in line.strip():
                    pkg_name = line.replace(" ", "").split("Name:")[1].strip()

                if "Version         :" in line.strip():
                    pkg_version = line.replace(" ", "").split("Version:")[1].strip()

                if "Repository      :" in line.strip():
                    pkg_repository = line.split("Repository      :")[1].strip()

                if "Description     :" in line.strip():
                    pkg_description = line.split("Description     :")[1].strip()

                if "Architecture    :" in line.strip():
                    pkg_arch = line.split("Architecture    :")[1].strip()

                if "URL             :" in line.strip():
                    pkg_url = line.split("URL             :")[1].strip()

                if "Depends On      :" in line.strip():
                    if line.split("Depends On      :")[1].strip() != "None":
                        pkg_depends_on_str = line.split("Depends On      :")[1].strip()

                        for pkg_dep in pkg_depends_on_str.split("  "):
                            pkg_depends_on.append((pkg_dep, None))
                    else:
                        pkg_depends_on = []

                if "Conflicts With  :" in line.strip():
                    if line.split("Conflicts With  :")[1].strip() != "None":
                        pkg_conflicts_with_str = line.split("Conflicts With  :")[
                            1
                        ].strip()

                        for pkg_con in pkg_conflicts_with_str.split("  "):
                            pkg_conflicts_with.append((pkg_con, None))
                    else:
                        pkg_conflicts_with = []

                if "Download Size   :" in line.strip():
                    pkg_download_size = line.split("Download Size   :")[1].strip()

                if "Installed Size  :" in line.strip():
                    pkg_installed_size = line.split("Installed Size  :")[1].strip()

                if "Build Date      :" in line.strip():
                    pkg_build_date = line.split("Build Date      :")[1].strip()

                if "Packager        :" in line.strip():
                    pkg_packager = line.split("Packager        :")[1].strip()

            package_metadata = {}

            package_metadata["name"] = pkg_name
            package_metadata["version"] = pkg_version
            package_metadata["repository"] = pkg_repository
            package_metadata["description"] = pkg_description
            package_metadata["arch"] = pkg_arch
            package_metadata["url"] = pkg_url
            package_metadata["depends_on"] = pkg_depends_on
            package_metadata["conflicts_with"] = pkg_conflicts_with
            package_metadata["download_size"] = pkg_download_size
            package_metadata["installed_size"] = pkg_installed_size
            package_metadata["build_date"] = pkg_build_date
            package_metadata["packager"] = pkg_packager

            return package_metadata

    except Exception as e:
        logger.error("Exception in get_package_information(): %e" % e)


# =====================================================
#               CREATE MESSAGE DIALOG
# =====================================================


def on_message_dialog_ok_response(self, dialog):
    dialog.hide()
    dialog.destroy()


def message_dialog(self, title, first_msg, secondary_msg):
    try:
        dialog = Gtk.Dialog(self)

        headerbar = Gtk.HeaderBar()
        headerbar.set_title(title)
        headerbar.set_show_close_button(True)

        dialog.set_default_size(800, 600)

        dialog.set_resizable(False)
        dialog.set_modal(True)
        dialog.set_border_width(10)

        dialog.set_titlebar(headerbar)
        dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        btn_ok = Gtk.Button(label="OK")
        btn_ok.set_size_request(100, 30)
        btn_ok.connect("clicked", on_message_dialog_ok_response, dialog)
        dialog.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))

        grid_message = Gtk.Grid()
        grid_message.set_column_homogeneous(True)
        grid_message.set_row_homogeneous(True)

        scrolled_window = Gtk.ScrolledWindow()
        textview = Gtk.TextView()
        textview.set_property("editable", False)
        textview.set_property("monospace", True)
        textview.set_vexpand(True)
        textview.set_hexpand(True)

        msg_buffer = textview.get_buffer()
        msg_buffer.insert(msg_buffer.get_end_iter(), " %s \n" % first_msg)
        msg_buffer.insert(msg_buffer.get_end_iter(), " %s \n" % secondary_msg)

        # move focus away from the textview, to hide the cursor at load
        headerbar.set_property("can-focus", True)
        Gtk.Window.grab_focus(headerbar)

        scrolled_window.add(textview)
        grid_message.attach(scrolled_window, 0, 0, 1, 1)

        lbl_padding = Gtk.Label(xalign=0, yalign=0)
        lbl_padding.set_name("lbl_btn_padding_right")

        lbl_padding_top1 = Gtk.Label(xalign=0)
        lbl_padding_top1.set_text("")

        lbl_padding_top2 = Gtk.Label(xalign=0)
        lbl_padding_top2.set_text("")

        lbl_btn_padding_right = Gtk.Label(xalign=0)
        lbl_btn_padding_right.set_name("lbl_btn_padding_right")

        grid_btn = Gtk.Grid()

        grid_btn.attach(lbl_padding_top1, 0, 1, 1, 1)
        grid_btn.attach(lbl_padding_top2, 0, 2, 1, 1)
        grid_btn.attach_next_to(
            lbl_btn_padding_right, lbl_padding_top2, Gtk.PositionType.RIGHT, 1, 1
        )

        grid_btn.attach_next_to(
            btn_ok, lbl_btn_padding_right, Gtk.PositionType.RIGHT, 1, 1
        )

        dialog.vbox.add(grid_message)
        dialog.vbox.add(grid_btn)

        dialog.show_all()

        return dialog
    except Exception as e:
        logger.error("Exception in message_dialog(): %s" % e)

    dialog.show_all()

    return dialog


# =====================================================
#               APP QUERY
# =====================================================


def get_current_installed():
    path = base_dir + "/cache/installed.lst"
    # query_str = "pacman -Q > " + path
    query_str = ["pacman", "-Q"]
    # run the query - using Popen because it actually suits this use case a bit better.

    subprocess_query = subprocess.Popen(
        query_str,
        shell=False,
        stdout=subprocess.PIPE,
    )

    out, err = subprocess_query.communicate(timeout=60)

    # added validation on process result
    if subprocess_query.returncode == 0:
        file = open(path, "w")
        for line in out.decode("utf-8"):
            file.write(line)
        file.close()
    else:
        logger.warning("Failed to run %s" % query_str)


def query_pkg(package):
    try:
        package = package.strip()
        path = base_dir + "/cache/installed.lst"

        if os.path.exists(path):
            if is_file_stale(path, 0, 0, 30):
                get_current_installed()
        # file does NOT exist;
        else:
            get_current_installed()
        # then, open the resulting list in read mode
        with open(path, "r") as f:
            # first we need to strip the new line escape sequence to ensure we don't get incorrect outcome
            pkg = package.strip("\n")

            # If the pkg name appears in the list, then it is installed
            for line in f:
                installed = line.split(" ")
                # We only compare against the name of the package, NOT the version number.
                if pkg == installed[0]:
                    # file.close()
                    return True
            # We will only hit here, if the pkg does not match anything in the file.
            # file.close()
        return False
    except Exception as e:
        logger.error("Exception in query_pkg(): %s " % e)


# =====================================================
#        PACKAGE DESCRIPTION CACHE AND SEARCH
# =====================================================


def cache(package, path_dir_cache):
    try:
        # first we need to strip the new line escape sequence to ensure we don't get incorrect outcome
        pkg = package.strip()
        # you can see all the errors here with the print command below
        if debug is True:
            print(pkg)
        # create the query
        query_str = ["pacman", "-Si", pkg, " --noconfirm"]

        # run the query - using Popen because it actually suits this use case a bit better.

        process = subprocess.Popen(
            query_str, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = process.communicate()

        # validate the process result
        if process.returncode == 0:
            if debug is True:
                logger.debug("Return code: equals 0 " + str(process.returncode))
            # out, err = process.communicate()

            output = out.decode("utf-8")

            if len(output) > 0:
                split = output.splitlines()

                # Currently the output of the pacman command above always puts the description on the 4th line.
                desc = str(split[3])
                # Ok, so this is a little fancy: there is formatting from the output which we wish to ignore (ends at 19th character)
                # and there is a remenant of it as the last character - usually a single or double quotation mark, which we also need to ignore
                description = desc[18:]
                # writing to a caching file with filename matching the package name
                filename = path_dir_cache + pkg

                file = open(filename, "w")
                file.write(description)
                file.close()

                return description
        # There are several packages that do not return a valid process return code
        # Cathing those manually via corrections folder
        if process.returncode != 0:
            if debug is True:
                print("Return code: " + str(process.returncode))
            exceptions = [
                "florence",
                "mintstick-bin",
                "arcolinux-conky-collection-plasma-git",
                "arcolinux-desktop-trasher-git",
                "arcolinux-pamac-all",
                "arcolinux-sddm-simplicity-git",
                "ttf-hack",
                "ttf-roboto-mono",
                "aisleriot",
                "mailspring",
                "linux-rt",
                "linux-rt-headers",
                "linux-rt-lts",
                "linux-rt-lts-headers",
                "arcolinux-sddm-simplicity-git",
                "kodi-x11",
                "kodi-addons",
                "sardi-icons",
            ]
            if pkg in exceptions:
                description = file_lookup(pkg, path_dir_cache + "corrections/")
                return description
        return "No Description Found"

    except Exception as e:
        logger.error("Exception in cache(): %s " % e)


# Creating an over-load so that we can use the same function, with slightly different code to get the results we need
def cache_btn():
    # fraction = 1 / len(packages)
    # Non Multithreaded version.
    packages.sort()
    number = 1
    for pkg in packages:
        logger.debug(str(number) + "/" + str(len(packages)) + ": Caching " + pkg)
        cache(pkg, path_dir_cache)
        number = number + 1
        # progressbar.timeout_id = GLib.timeout_add(50, progressbar.update, fraction)

    logger.debug("Caching applications finished")

    # This will need to be coded to be running multiple processes eventually, since it will be manually invoked.
    # process the file list
    # for each file in the list, open the file
    # process the file ignoring what is not what we need
    # for each file line processed, we need to invoke the cache function that is not over-ridden.


def file_lookup(package, path):
    # first we need to strip the new line escape sequence to ensure we don't get incorrect outcome
    pkg = package.strip("\n")
    output = ""
    if os.path.exists(path + "corrections/" + pkg):
        filename = path + "corrections/" + pkg
    else:
        filename = path + pkg
    file = open(filename, "r")
    output = file.read()
    file.close()
    if len(output) > 0:
        return output
    return "No Description Found"


def obtain_pkg_description(package):
    # This is a pretty simple function now, decide how to get the information, then get it.
    # processing variables.
    output = ""
    path = base_dir + "/cache/"

    # First we need to determine whether to pull from cache or pacman.
    if os.path.exists(path + package.strip("\n")):
        output = file_lookup(package, path)

    # file doesn't exist, so create a blank copy
    else:
        output = cache(package, path)
    # Add the package in question to the global variable, in case recache is needed
    packages.append(package)
    return output


def restart_program():
    os.unlink("/tmp/sofirem.lock")
    python = sys.executable
    os.execl(python, python, *sys.argv)


# def check_github(yaml_files):
#     # This is the link to the location where the .yaml files are kept in the github
#     # Removing desktop wayland, desktop, drivers, nvidia, ...
#     path = base_dir + "/cache/"
#     link = "https://github.com/arcolinux/arcob-calamares-config-awesome/tree/master/calamares/modules/"
#     urls = []
#     fns = []
#     for file in yaml_files:
#         if isfileStale(path + file, 14, 0, 0):
#             fns.append(path + file)
#             urls.append(link + file)
#     if len(fns) > 0 & len(urls) > 0:
#         inputs = zip(urls, fns)
#         download_parallel(inputs)


# def download_url(args):
#     t0 = time.time()
#     url, fn = args[0], args[1]
#     try:
#         r = requests.get(url)
#         with open(fn, "wb") as f:
#             f.write(r.content)
#         return (url, time.time() - t0)
#     except Exception as e:
#         print("Exception in download_url():", e)


# def download_parallel(args):
#     cpus = cpu_count()
#     results = ThreadPool(cpus - 1).imap_unordered(download_url, args)
#     for result in results:
#         print("url:", result[0], "time (s):", result[1])


# =====================================================
#               CHECK RUNNING PROCESS
# =====================================================


def checkIfProcessRunning(process_name):
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=["pid", "name", "create_time"])
            if process_name == pinfo["pid"]:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


# =====================================================
#               MONITOR PACMAN LOG FILE
# =====================================================


# write lines from the pacman log onto a queue, this is called from a non-blocking thread
def addPacmanLogQueue(self):
    try:
        lines = []
        with open(pacman_logfile, "r") as f:
            while True:
                line = f.readline()
                if line:
                    lines.append(line)
                    self.pacmanlog_queue.put(lines)
                else:
                    time.sleep(0.5)

    except Exception as e:
        logger.error("Exception in addPacmanLogQueue() : %s" % e)
    finally:
        logger.debug("No new lines found inside the pacman log file")


# update the textview called from a non-blocking thread
def startLogTimer(self):
    while True:
        GLib.idle_add(updateTextView, self, priority=GLib.PRIORITY_DEFAULT)
        time.sleep(2)

        if self.start_logtimer is False:
            return False


# update the textview component with new lines from the pacman log file
def updateTextView(self):
    lines = self.pacmanlog_queue.get()

    try:
        if len(lines) > 0:
            end_iter = self.buffer.get_end_iter()

            for line in lines:
                self.buffer.insert(end_iter, "  %s" % line, len("  %s" % line))

    except Exception as e:
        logger.error("Exception in updateTextView() : %s" % e)
    finally:
        self.pacmanlog_queue.task_done()

        if len(lines) > 0:
            text_mark_end = self.buffer.create_mark(
                "end", self.buffer.get_end_iter(), False
            )
            # auto-scroll the textview to the bottom as new content is added
            self.pacmanlog_textview.scroll_mark_onscreen(text_mark_end)

        lines.clear()


# this gets info on the pacman process currently running
def get_pacman_process():
    try:
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=["pid", "name", "create_time"])
                if pinfo["name"] == "pacman":
                    return " ".join(proc.cmdline())

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        logger.error("Exception in get_pacman_process() : %s" % e)


# =====================================================
#               MESSAGEBOX
# =====================================================


def messageBox(self, title, message):
    md2 = Gtk.MessageDialog(
        parent=self,
        flags=0,
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    md2.format_secondary_markup(message)
    md2.run()
    md2.destroy()


# =====================================================
#               USER SEARCH
# =====================================================


def search(self, term):
    try:
        logger.info('Searching for: "%s"' % term)

        pkg_matches = []

        category_dict = {}

        whitespace = False

        if term.strip():
            whitespace = True

        for pkg_list in self.packages.values():
            for pkg in pkg_list:
                if whitespace:
                    for te in term.split(" "):
                        if (
                            te.lower() in pkg.name.lower()
                            or te.lower() in pkg.description.lower()
                        ):
                            # only unique name matches
                            if pkg not in pkg_matches:
                                pkg_matches.append(
                                    pkg,
                                )
                else:
                    if (
                        term.lower() in pkg.name.lower()
                        or term.lower() in pkg.description.lower()
                    ):
                        pkg_matches.append(
                            pkg,
                        )

        # filter the results so that each category holds a list of package

        category_name = None
        packages_cat = []
        for pkg_match in pkg_matches:
            if category_name == pkg_match.category:
                packages_cat.append(pkg_match)
                category_dict[category_name] = packages_cat
            elif category_name is None:
                packages_cat.append(pkg_match)
                category_dict[pkg_match.category] = packages_cat
            else:
                # reset packages, new category
                packages_cat = []

                packages_cat.append(pkg_match)

                category_dict[pkg_match.category] = packages_cat

            category_name = pkg_match.category

        if len(category_dict) == 0:
            self.search_queue.put(None)
            msg_dialog = message_dialog(
                self,
                "Find Package",
                "The search term was not found in the available sources.",
                "Please try another search query.",
            )

            msg_dialog.show_all()

            msg_dialog.hide()
            msg_dialog.destroy()

        # debug console output to display package info
        """
        # print out number of results found from each category
        print("[DEBUG] %s Search results.." % datetime.now().strftime("%H:%M:%S"))

        for category in sorted(category_dict):
            category_res_len = len(category_dict[category])
            print("[DEBUG] %s %s = %s" %(
                        datetime.now().strftime("%H:%M:%S"),
                        category,
                        category_res_len,
                    )
            )
        """

        # sort dictionary so the category names are displayed in alphabetical order
        sorted_dict = None

        if len(category_dict) > 0:
            sorted_dict = dict(sorted(category_dict.items()))
            self.search_queue.put(
                sorted_dict,
            )
        else:
            return

    except Exception as e:
        logger.error("Exception in search(): %s", e)


# =====================================================
#               ARCOLINUX REPOS, KEYS AND MIRRORS
# =====================================================


def append_repo(text):
    """Append a new repo"""
    try:
        with open(pacman_conf, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(text)
    except Exception as e:
        logger.error("Exception in append_repo(): %s" % e)


def repo_exist(value):
    """check repo_exists"""
    with open(pacman_conf, "r", encoding="utf-8") as f:
        lines = f.readlines()
        f.close()

    for line in lines:
        if value in line:
            return True
    return False


# install ArcoLinux mirrorlist and key package
def install_arcolinux_key_mirror():
    base_dir = os.path.dirname(os.path.realpath(__file__))
    pathway = base_dir + "/packages/arcolinux-keyring/"
    file = os.listdir(pathway)

    try:
        install = "pacman -U " + pathway + str(file).strip("[]'") + " --noconfirm"
        logger.info("Install command = %s" % install)
        subprocess.call(
            install.split(" "),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        logger.info("ArcoLinux keyring is now installed")
    except Exception as e:
        logger.error("Exception in install_arcolinux_key_mirror(): %s" % e)

    pathway = base_dir + "/packages/arcolinux-mirrorlist/"
    file = os.listdir(pathway)
    try:
        install = "pacman -U " + pathway + str(file).strip("[]'") + " --noconfirm"
        logger.info("Command = %s" % install)
        subprocess.call(
            install.split(" "),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        logger.info("ArcoLinux mirrorlist is now installed")
    except Exception as e:
        logger.error("Exception in install_arcolinux_key_mirror(): %s" % e)


# remove ArcoLinux mirrorlist and key package
def remove_arcolinux_key_mirror(self):
    try:
        command = "pacman -Rdd arcolinux-keyring --noconfirm"
        logger.info("Command = %s " % command)
        subprocess.call(
            command.split(" "),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        logger.info("ArcoLinux keyring is now removed")
    except Exception as e:
        logger.error("Exception in remove_arcolinux_key_mirror(): %s" % e)

    try:
        command = "pacman -Rdd arcolinux-mirrorlist-git --noconfirm"
        logger.info("Command = %s " % command)
        subprocess.call(
            command.split(" "),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        logger.info("ArcoLinux mirrorlist is now removed")
    except Exception as e:
        logger.error("Exception in remove_arcolinux_key_mirror(): %s" % e)


def add_repos():
    """add the ArcoLinux repos in /etc/pacman.conf"""
    if distr == "arcolinux":
        logger.info("Adding ArcoLinux repos on ArcoLinux")
        try:
            with open(pacman_conf, "r", encoding="utf-8") as f:
                lines = f.readlines()
                f.close()
        except Exception as e:
            logger.error("Exception in add_repos(): %s" % e)

        text = "\n\n" + atestrepo + "\n\n" + arepo + "\n\n" + a3prepo + "\n\n" + axlrepo

        pos = get_position(lines, "#[testing]")
        lines.insert(pos - 2, text)

        try:
            with open(pacman_conf, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            logger.error("Exception in add_repos(): %s" % e)
    else:
        if not repo_exist("[arcolinux_repo_testing]"):
            logger.info("Adding ArcoLinux test repo (not used)")
            append_repo(atestrepo)
        if not repo_exist("[arcolinux_repo]"):
            logger.info("Adding ArcoLinux repo")
            append_repo(arepo)
        if not repo_exist("[arcolinux_repo_3party]"):
            logger.info("Adding ArcoLinux 3th party repo")
            append_repo(a3prepo)
        if not repo_exist("[arcolinux_repo_xlarge]"):
            logger.info("Adding ArcoLinux XL repo")
            append_repo(axlrepo)
        if repo_exist("[arcolinux_repo]"):
            logger.info("ArcoLinux repos have been installed")


def remove_repos():
    """remove the ArcoLinux repos in /etc/pacman.conf"""
    try:
        with open(pacman_conf, "r", encoding="utf-8") as f:
            lines = f.readlines()
            f.close()

        if repo_exist("[arcolinux_repo_testing]"):
            pos = get_position(lines, "[arcolinux_repo_testing]")
            del lines[pos + 3]
            del lines[pos + 2]
            del lines[pos + 1]
            del lines[pos]

        if repo_exist("[arcolinux_repo]"):
            pos = get_position(lines, "[arcolinux_repo]")
            del lines[pos + 3]
            del lines[pos + 2]
            del lines[pos + 1]
            del lines[pos]

        if repo_exist("[arcolinux_repo_3party]"):
            pos = get_position(lines, "[arcolinux_repo_3party]")
            del lines[pos + 3]
            del lines[pos + 2]
            del lines[pos + 1]
            del lines[pos]

        if repo_exist("[arcolinux_repo_xlarge]"):
            pos = get_position(lines, "[arcolinux_repo_xlarge]")
            del lines[pos + 2]
            del lines[pos + 1]
            del lines[pos]

        with open(pacman_conf, "w", encoding="utf-8") as f:
            f.writelines(lines)
            f.close()

    except Exception as e:
        logger.error("Exception in remove_repos(): %s" % e)


# =====================================================
#               CHECK IF PACKAGE IS INSTALLED
# =====================================================

# avoid using shell=True since there are security considerations
# https://docs.python.org/3.8/library/subprocess.html#security-considerations


# check if package is installed or not
def check_package_installed(package):
    query_str = ["pacman", "-Qi", package]
    try:
        process_pkg_installed = subprocess.run(
            query_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
        )
        # package is installed
        if process_pkg_installed.returncode == 0:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        # package is not installed
        return False


# =====================================================
#               NOTIFICATIONS
# =====================================================


def show_in_app_notification(self, message, err):
    if self.timeout_id is not None:
        GLib.source_remove(self.timeout_id)
        self.timeout_id = None

    if err is True:
        self.notification_label.set_markup(
            '<span background="yellow" foreground="black">' + message + "</span>"
        )
    else:
        self.notification_label.set_markup(
            '<span foreground="white">' + message + "</span>"
        )
    self.notification_revealer.set_reveal_child(True)
    self.timeout_id = GLib.timeout_add(3000, timeout, self)


def timeout(self):
    close_in_app_notification(self)


def close_in_app_notification(self):
    self.notification_revealer.set_reveal_child(False)
    GLib.source_remove(self.timeout_id)
    self.timeout_id = None


def reveal_infobar(self, progress_dialog):
    progress_dialog.infobar.set_revealed(True)
    progress_dialog.infobar.show_all()
    GLib.source_remove(self.timeout_id)
    self.timeout_id = None


"""
    Since the app could be quit/terminated at any time during a pacman transaction.
    The pacman process spawned by the install/uninstall threads, needs to be terminated too.
    Otherwise the app may hang waiting for pacman to complete its transaction.
"""


def terminate_pacman():
    try:
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=["pid", "name", "create_time"])
                if pinfo["name"] == "pacman":
                    logger.debug("Killing pacman process = %s" % pinfo["name"])

                    proc.kill()

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if check_pacman_lockfile():
            os.unlink(pacman_lockfile)
    except Exception as e:
        logger.error("Exception in terminate_pacman() : %s" % e)


def is_thread_alive(thread_name):
    for thread in threading.enumerate():
        if thread.name == thread_name and thread.is_alive():
            return True

    return False


# for debugging print number of threads running
def print_threads_alive():
    for thread in threading.enumerate():
        if thread.is_alive():
            logger.debug("Thread alive = %s" % thread.name)


# check if pacman lock file exists
def check_pacman_lockfile():
    try:
        if os.path.exists(pacman_lockfile):
            logger.warning("Pacman lockfile found inside %s" % pacman_lockfile)
            logger.warning("Another pacman process is running")
            return True
        else:
            logger.info("No pacman lockfile found, ok to proceed")
            return False
    except Exception as e:
        logger.error("Exception in check_pacman_lockfile() : %s" % e)


# =====================================================
#               SETTINGS
# =====================================================


def on_dialog_export_clicked(self, dialog, packages_lst):
    try:
        filename = "%s/sofirem-export.txt" % home

        with open(filename, "w", encoding="utf-8") as f:
            f.write(
                "# Created by Sofirem on %s\n"
                % datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            for package in packages_lst:
                f.write("%s\n" % (package[0]))

        if os.path.exists(filename):
            logger.info("Export completed")

            # fix permissions, file is owned by root
            permissions(filename)

            msg_dialog = message_dialog(
                self,
                "Package export complete",
                "Package list exported to %s" % filename,
                "",
            )

            msg_dialog.set_modal(True)

            msg_dialog.show_all()
            msg_dialog.run()
            msg_dialog.hide()
        else:
            logger.error("Export failed")
            msg_dialog = message_dialog(
                self,
                "Package export failed",
                "Failed to export package list to %s." % filename,
                "",
            )

            msg_dialog.show_all()
            msg_dialog.run()
            msg_dialog.hide()
    except Exception as e:
        logger.error("Exception in on_dialog_export_clicked(): %s" % e)


def on_dialog_export_close_clicked(self, dialog):
    dialog.hide()
    dialog.destroy()


def on_dialog_export_on_close(self, event, dialog):
    dialog.hide()
    dialog.destroy()


# export currently installed packages to a txt file inside $HOME
def export_installed_packages(self):
    try:
        # display dialog, showing installed export button with list of packages

        export_dialog = Gtk.Dialog()
        export_dialog.set_resizable(False)
        export_dialog.set_size_request(900, 700)
        export_dialog.set_modal(True)
        export_dialog.set_border_width(10)
        export_dialog.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))

        export_dialog.connect("delete-event", on_dialog_export_on_close, export_dialog)

        headerbar = Gtk.HeaderBar()
        headerbar.set_title("Showing installed packages")
        headerbar.set_show_close_button(True)

        export_dialog.set_titlebar(headerbar)

        export_grid = Gtk.Grid()
        export_grid.set_column_homogeneous(True)

        # get a list of installed packages on the system

        packages_lst = get_installed_package_data()

        if len(packages_lst) > 0:
            export_dialog.set_title("Showing %s installed packages" % len(packages_lst))
            logger.debug("List of installed packages obtained")

            treestore_packages = Gtk.TreeStore(str, str, str, str)
            for item in packages_lst:
                treestore_packages.append(None, list(item))

            treeview_packages = Gtk.TreeView()

            treeview_packages.set_model(treestore_packages)

            for i, col_title in enumerate(
                ["Name", "Version", "Installed Date", "Installed Size"]
            ):
                renderer = Gtk.CellRendererText()
                col = Gtk.TreeViewColumn(col_title, renderer, text=i)
                treeview_packages.append_column(col)

            path = Gtk.TreePath.new_from_indices([0])

            selection = treeview_packages.get_selection()
            selection.select_path(path)

            treeview_packages.expand_all()
            treeview_packages.columns_autosize()

            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_vexpand(True)

            export_grid.attach(scrolled_window, 0, 0, 8, 10)

            lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding1.set_text("")

            export_grid.attach_next_to(
                lbl_padding1, scrolled_window, Gtk.PositionType.BOTTOM, 1, 1
            )

            btn_dialog_export = Gtk.Button(label="Export")
            btn_dialog_export.connect(
                "clicked", on_dialog_export_clicked, export_dialog, packages_lst
            )
            btn_dialog_export.set_size_request(100, 30)
            # btn_dialog_export.set_halign(Gtk.Align.END)

            btn_dialog_export_close = Gtk.Button(label="Close")
            btn_dialog_export_close.connect(
                "clicked", on_dialog_export_close_clicked, export_dialog
            )
            btn_dialog_export_close.set_size_request(100, 30)

            btn_grid = Gtk.Grid()

            lbl_btn_padding_right = Gtk.Label(xalign=0, yalign=0)

            # padding to make the buttons move across to the right of the dialog
            # set the name of the label using the value set inside the sofirem.css file

            lbl_btn_padding_right.set_name("lbl_btn_padding_right")

            btn_grid.attach(lbl_btn_padding_right, 0, 0, 1, 1)

            lbl_padding2 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding2.set_text("     ")

            btn_grid.attach_next_to(
                btn_dialog_export, lbl_btn_padding_right, Gtk.PositionType.RIGHT, 1, 1
            )

            btn_grid.attach_next_to(
                lbl_padding2, btn_dialog_export, Gtk.PositionType.RIGHT, 1, 1
            )

            btn_grid.attach_next_to(
                btn_dialog_export_close, lbl_padding2, Gtk.PositionType.RIGHT, 1, 1
            )

            scrolled_window.add(treeview_packages)

            export_dialog.vbox.add(export_grid)
            export_dialog.vbox.add(btn_grid)
            export_dialog.show_all()
            export_dialog.run()

        else:
            logger.error("Failed to obtain list of installed packages")

    except Exception as e:
        logger.error("Exception in export_installed_packages(): %s" % e)


# ANYTHING UNDER THIS LINE IS CURRENTLY UNUSED!


# =====================================================
#              PACMAN LOCK FILE THREADING
# =====================================================
"""
def waitForPacmanLockFile():
    start = int(time.time())

    try:
        while True:
            if check_pacman_lockfile():
                time.sleep(2)

                elapsed = int(time.time()) + 2

                logger.debug("Pacman status = Busy | Elapsed duration = %ss")

                proc = get_pacman_process()

                if proc:
                    logger.debug("Pacman process running: %s" % proc)

                else:
                    logger.debug("Process completed, Pacman status = Ready")
                    return

                if (elapsed - start) >= process_timeout:
                    logger.warning(
                        "Waiting for previous Pacman transaction to complete timed out after %ss"
                        % process_timeout
                    )

                    return
            else:
                logger.debug("Pacman status = Ready")
                return
    except Exception as e:
        logger.error("Exception in waitForPacmanLockFile(): %s " % e)
"""
