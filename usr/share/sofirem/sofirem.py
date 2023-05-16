#!/usr/bin/env python3
import Splash
import gi
import os
import Functions as fn
from ProgressBarWindow import ProgressBarWindow
import signal
import datetime
import GUI
import subprocess
from Functions import os
from queue import Queue
import App_Frame_GUI
from About import About

# from Functions import install_alacritty, os, pacman
from subprocess import PIPE, STDOUT
from time import sleep
from datetime import datetime
import sys
import time

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib  # noqa

#      #============================================================
#      #=  Authors:  Erik Dubois - Cameron Percival   - Fennec     =
#      #============================================================

# Folder structure

# cache contains descriptions - inside we have corrections for manual intervention
# + installed applications list
# yaml is the folder that is used to create the application
# yaml-awesome is a copy/paste from Calamares to meld manually - not used in the app

base_dir = os.path.dirname(os.path.realpath(__file__))
debug = True


class Main(Gtk.Window):
    # Create a queue, for worker communication (Multithreading - used in GUI layer)
    queue = Queue()

    # Create a queue to handle package install/removal
    pkg_queue = Queue()

    # Create a queue for storing search results
    search_queue = Queue()

    # Create a queue for storing Pacman log file contents
    pacmanlog_queue = Queue()

    def __init__(self):
        try:
            super(Main, self).__init__(title="Sofirem")
            self.set_border_width(10)
            self.connect("delete-event", self.on_close)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))
            self.set_default_size(1100, 900)
            # ctrl+f give focus to search entry
            self.connect("key-press-event", self.on_keypress_event)
            self.timeout_id = None
            # default: displaying versions are disabled
            self.display_versions = False

            # self.package_metadata = fn.get_package_information(self, "gimp")
            # pkg = fn.Package(
            #     "wine-staging",
            #     "description",
            #     "category",
            #     "subcategory",
            #     "subcategory_description",
            #     "version",
            # )
            # dialog = fn.create_package_progress_dialog(
            #     self,
            #     "install",
            #     pkg,
            #     "pacman -s paru --noconfirm",
            # )
            #
            # sys.exit(0)

            print(
                "---------------------------------------------------------------------------"
            )
            print("If you have errors, report it on the discord channel of ArcoLinux")
            print(
                "---------------------------------------------------------------------------"
            )
            print("You can receive support on https://discord.gg/stBhS4taje")
            print(
                "---------------------------------------------------------------------------"
            )
            print(
                "Many applications are coming from the Arch Linux repos and can be installed"
            )
            print(
                "without any issues. Other applications are available from third party repos"
            )
            print("like Chaotic repo, ArcoLinux repo and others.")
            print(
                "---------------------------------------------------------------------------"
            )
            print("We do NOT build packages from AUR.")
            print(
                "---------------------------------------------------------------------------"
            )
            print("Some packages are only available on the ArcoLinux repos.")
            print(
                "---------------------------------------------------------------------------"
            )

            # Fetch list of packages already installed before the app makes changes
            fn.create_packages_log()

            fn.logger.info("pkgver = pkgversion")
            fn.logger.info("pkgrel = pkgrelease")
            print(
                "---------------------------------------------------------------------------"
            )
            fn.logger.info("Distro = " + fn.distr)
            print(
                "---------------------------------------------------------------------------"
            )

            # Create installed.lst file for first time
            fn.get_current_installed()
            fn.logger.info("Created installed.lst")
            # start making sure sofirem starts next time with dark or light theme
            if os.path.isdir(fn.home + "/.config/gtk-3.0"):
                try:
                    if not os.path.islink("/root/.config/gtk-3.0"):
                        fn.shutil.rmtree("/root/.config/gtk-3.0")
                        fn.shutil.copytree(
                            fn.home + "/.config/gtk-3.0", "/root/.config/gtk-3.0"
                        )
                except Exception as error:
                    print(error)

            if os.path.isdir("/root/.config/xsettingsd/xsettingsd.conf"):
                try:
                    if not os.path.islink("/root/.config/xsettingsd/"):
                        fn.shutil.rmtree("/root/.config/xsettingsd/")
                        if fn.path.isdir(fn.home + "/.config/xsettingsd/"):
                            fn.shutil.copytree(
                                fn.home + "/.config/xsettingsd/",
                                "/root/.config/xsettingsd/",
                            )
                except Exception as error:
                    print(error)

            # test there is no pacman lock file on the system
            if fn.check_pacman_lockfile():
                dialog = fn.message_dialog(
                    self,
                    "Pacman lock file",
                    "Pacman lock file found inside %s" % fn.pacman_lockfile,
                    "Is there another Pacman process running ?",
                )
                dialog.run()
                dialog.destroy()
                sys.exit(1)

            # run pacman -Sy to sync pacman db, else you get a lot of 404 errors

            sync_err = fn.sync_package_db()

            if sync_err is not None:
                fn.logger.error("[ERROR] Synchronising failed")

                print(
                    "---------------------------------------------------------------------------"
                )

                dialog = fn.message_dialog(
                    self,
                    "Pacman synchronisation failed",
                    "Failed to run command = pacman -Sy\nPacman db synchronisation failed\nCheck the synchronisation logs, and verify you can connect to the appropriate mirrors\n\n",
                    sync_err,
                )

                dialog.run()
                dialog.destroy()
                sys.exit(1)

            else:
                fn.logger.info("Synchronising complete")

            # store package information into memory, and use the dictionary returned to search in for quicker retrieval
            fn.logger.info("Storing package metadata started")

            self.packages = fn.storePackages()

            fn.logger.info("Categories = %s" % len(self.packages.keys()))

            total_packages = 0

            for category in self.packages:
                total_packages += len(self.packages[category])

            fn.logger.info("Total packages = %s" % total_packages)

            fn.logger.info("Storing package metadata completed")

            splScr = Splash.splashScreen()

            while Gtk.events_pending():
                Gtk.main_iteration()

            sleep(3)
            splScr.destroy()

            fn.logger.info("Preparing GUI")

            # On initial app load search_activated is set to False

            self.search_activated = False

            # Save reference to the vbox generated from the main GUI view
            GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)

            fn.logger.info("GUI loaded")

            if not os.path.isfile("/tmp/sofirem.lock"):
                with open("/tmp/sofirem.lock", "w") as f:
                    f.write("")

        except Exception as e:
            fn.logger.error("Exception in Main() : %s" % e)

    # =====================================================
    #               WINDOW KEY EVENT CTRL + F
    # =====================================================

    # sets focus on the search entry
    def on_keypress_event(self, widget, event):
        shortcut = Gtk.accelerator_get_label(event.keyval, event.state)

        if shortcut in ("Ctrl+F", "Ctrl+Mod2+F"):
            # set focus on text entry, select all text if any
            self.searchEntry.grab_focus()

        if shortcut in ("Ctrl+I", "Ctrl+Mod2+I"):
            fn.show_package_info(self)

    # =====================================================
    #               SEARCH ENTRY
    # =====================================================

    def on_search_activated(self, searchentry):
        if searchentry.get_text_length() == 0 and self.search_activated:
            GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)
            self.search_activated = False

        if searchentry.get_text_length() == 0:
            self.search_activated = False

        search_term = searchentry.get_text()
        # if the string is completely whitespace ignore searching
        if not search_term.isspace():
            try:
                if len(search_term) > 0:
                    # test if the string entered by the user is in the package name
                    # results is a dictionary, which holds a list of packages
                    # results[category]=pkg_list

                    # searching is processed inside a thread

                    th_search = fn.threading.Thread(
                        name="thread_search",
                        target=fn.search,
                        args=(
                            self,
                            search_term,
                        ),
                    )
                    fn.logger.info("Starting search")

                    th_search.start()

                    # get the search_results from the queue
                    results = self.search_queue.get()

                    if results is not None:
                        fn.logger.info("Search complete")

                        if len(results) > 0:
                            total = 0
                            for val in results.values():
                                total += len(val)

                            fn.logger.info("Search found %s results" % total)
                            # make sure the gui search only displays the pkgs inside the results

                            GUI.GUISearch(
                                self,
                                Gtk,
                                Gdk,
                                GdkPixbuf,
                                base_dir,
                                os,
                                Pango,
                                results,
                                search_term,
                            )

                            self.search_activated = True
                    else:
                        fn.logger.info("Search found %s results" % 0)
                        self.searchEntry.grab_focus()

                        msg_dialog = fn.message_dialog(
                            self,
                            "Search returned 0 results",
                            "Failed to find search term inside either the package name / description.",
                            "Try searching for something else.",
                        )

                        msg_dialog.show_all()
                        msg_dialog.run()
                        msg_dialog.hide()

                elif self.search_activated == True:
                    GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)
                    self.search_activated = False
            except Exception as err:
                fn.logger.error("Exception in on_search_activated(): %s" % err)

            finally:
                if self.search_activated == True:
                    self.search_queue.task_done()

    def on_search_cleared(self, searchentry, icon_pos, event):
        if self.search_activated:
            GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)

        self.searchEntry.set_placeholder_text("Search...")

        self.search_activated = False

    # =====================================================
    #               ARCOLINUX REPOS, KEYS AND MIRRORS
    # =====================================================

    def on_repos_clicked(self, widget):
        if self.btnRepos._value == 1:
            fn.logger.info("Let's install the ArcoLinux keys and mirrors")
            fn.install_arcolinux_key_mirror(self)

            fn.logger.info("Checking whether the repos have been added")
            fn.add_repos()

            self.btnRepos.set_label("Remove ArcoLinux Repos")
            self.btnRepos._value = 2

        else:
            fn.logger.info("Let's remove the ArcoLinux keys and mirrors")
            fn.remove_arcolinux_key_mirror(self)
            fn.logger.info("Removing the ArcoLinux repos in /etc/pacman.conf")
            fn.remove_repos()

            self.btnRepos.set_label("Add ArcoLinux Repos")
            self.btnRepos._value = 1

    # =====================================================
    #               RESTART/QUIT BUTTON
    # =====================================================

    def on_close(self, widget, data):
        if os.path.exists("/tmp/sofirem.lock"):
            os.unlink("/tmp/sofirem.lock")

        if os.path.exists("/tmp/sofirem.pid"):
            os.unlink("/tmp/sofirem.pid")

        # see the comment in fn.terminate_pacman()
        fn.terminate_pacman()

        Gtk.main_quit()
        print(
            "---------------------------------------------------------------------------"
        )
        print("Thanks for using Sofirem")
        print("Report issues to make it even better")
        print(
            "---------------------------------------------------------------------------"
        )
        print("You can report issues on https://discord.gg/stBhS4taje")
        print(
            "---------------------------------------------------------------------------"
        )

    # ====================================================================
    #                     Button Functions
    # ====================================================================
    # Given what this function does, it might be worth considering making it a
    # thread so that the app doesn't block while installing/uninstalling is happening.
    def app_toggle(self, widget, active, package):
        # switch widget is currently toggled off
        if widget.get_state() == False and widget.get_active() == True:
            if len(package.name) > 0:
                # widget.set_active(True)
                # widget.set_state(True)

                # check there is no pacman lockfile before continuing
                if fn.check_pacman_lockfile() is False:
                    self.package_metadata = fn.get_package_information(
                        self, package.name
                    )
                    fn.logger.info("Package to install : %s" % package.name)

                    self.pkg_queue.put(
                        (
                            package,
                            "install",
                            widget,
                        ),
                    )

                    th = fn.threading.Thread(
                        name="thread_pkginst",
                        target=fn.install,
                        args=(self,),
                    )

                    th.start()
                else:
                    proc = fn.get_pacman_process()
                    dialog = fn.message_dialog(
                        self,
                        "Pacman lockfile found",
                        "Pacman is busy and is processing another transaction",
                        "Process currently running = %s" % proc,
                    )
                    dialog.show_all()
                    dialog.run()
                    dialog.hide()

        # switch widget is currently toggled on
        if widget.get_state() == True and widget.get_active() == False:
            # Uninstall the package
            # widget.set_active(False)
            # widget.set_state(False)
            if len(package.name) > 0:
                if fn.check_pacman_lockfile() is False:
                    self.package_metadata = fn.get_package_information(
                        self, package.name
                    )
                    fn.logger.info("Package to remove : %s" % package.name)

                    self.pkg_queue.put(
                        (
                            package,
                            "uninstall",
                            widget,
                        ),
                    )

                    th = fn.threading.Thread(
                        name="thread_pkgrem",
                        target=fn.uninstall,
                        args=(self,),
                    )

                    th.start()
                else:
                    proc = fn.get_pacman_process()
                    dialog = fn.message_dialog(
                        self,
                        "Pacman lockfile found",
                        "Pacman is busy and is processing another transaction",
                        "Process currently running = %s" % proc,
                    )
                    dialog.show_all()
                    dialog.run()
                    dialog.hide()

        fn.get_current_installed()
        fn.print_threads_alive()

        # return True to prevent the default handler from running
        return True

        # App_Frame_GUI.GUI(self, Gtk, vboxStack1, fn, category, package_file)
        # widget.get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().queue_redraw()
        # self.gui.hide()
        # self.gui.queue_redraw()
        # self.gui.show_all()

    def recache_clicked(self, widget):
        # Check if cache is out of date. If so, run the re-cache, if not, don't.
        # pb = ProgressBarWindow()
        # pb.show_all()
        # pb.set_text("Updating Cache")
        # pb.reset_timer()

        fn.logger.info("Recache applications - start")

        fn.cache_btn()

    # ================================================================
    #                   SETTINGS
    # ================================================================

    def on_about_app_clicked(self, widget):
        fn.logger.info("Showing About dialog")
        self.toggle_popover()

        about = About()
        about.run()

    def on_packages_export_clicked(self, widget):
        self.toggle_popover()
        GLib.idle_add(
            fn.export_installed_packages,
            self,
            priority=GLib.PRIORITY_DEFAULT,
        )

    def toggle_popover(self):
        if self.popover.get_visible():
            self.popover.hide()
        else:
            self.popover.show_all()

    def on_settings_clicked(self, widget):
        self.toggle_popover()

    def version_toggle(self, widget, data):
        if widget.get_active() == True:
            fn.logger.info("Showing package versions")
            self.display_versions = True
            GLib.idle_add(
                self.refresh_main_gui,
                priority=GLib.PRIORITY_DEFAULT,
            )
        else:
            fn.logger.info("Hiding package versions")
            self.display_versions = False
            GLib.idle_add(
                self.refresh_main_gui,
                priority=GLib.PRIORITY_DEFAULT,
            )

    def refresh_main_gui(self):
        self.remove(self.vbox)
        GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)
        self.show_all()

    def on_pacman_log_clicked(self, widget):
        try:
            self.toggle_popover()
            thread_addlog = "thread_addPacmanLogQueue"
            thread_add_pacmanlog_alive = fn.is_thread_alive(thread_addlog)

            if thread_add_pacmanlog_alive == False:
                fn.logger.info("Starting thread to monitor Pacman Log file")

                th_add_pacmanlog_queue = fn.threading.Thread(
                    name=thread_addlog,
                    target=fn.addPacmanLogQueue,
                    args=(self,),
                    daemon=True,
                )
                th_add_pacmanlog_queue.start()

            else:
                fn.logger.info("Thread to monitor Pacman Log file is already active")

            # show dialog

            pacmanlog_dialog = Gtk.Dialog(self)
            pacmanlog_headerbar = Gtk.HeaderBar()

            pacmanlog_headerbar.set_show_close_button(True)

            pacmanlog_dialog.set_titlebar(pacmanlog_headerbar)

            pacmanlog_dialog.set_title("Pacman log file viewer")
            pacmanlog_dialog.set_default_size(700, 600)
            btnPacmanLogOk = Gtk.Button(label="OK")
            btnPacmanLogOk.connect(
                "clicked", self.onPacmanlogResponse, pacmanlog_dialog
            )
            pacmanlog_dialog.set_icon_from_file(
                os.path.join(base_dir, "images/sofirem.png")
            )

            pacmanlog_grid = Gtk.Grid()
            pacmanlog_grid.set_column_homogeneous(True)
            pacmanlog_grid.set_row_homogeneous(True)

            pacmanlog_scrolledwindow = Gtk.ScrolledWindow()

            if thread_add_pacmanlog_alive == True:
                # thread already running, textbuffer already populated
                # re-use the existing textbuffer to repopulate the textviewer
                self.pacmanlog_textview = Gtk.TextView()
                self.pacmanlog_textview.set_property("editable", False)
                self.pacmanlog_textview.set_property("monospace", True)
                self.pacmanlog_textview.set_vexpand(True)
                self.pacmanlog_textview.set_hexpand(True)
                self.pacmanlog_textview.set_buffer(self.buffer)
            else:
                self.pacmanlog_textview = Gtk.TextView()
                self.pacmanlog_textview.set_property("editable", False)
                self.pacmanlog_textview.set_property("monospace", True)
                self.pacmanlog_textview.set_vexpand(True)
                self.pacmanlog_textview.set_hexpand(True)
                self.buffer = self.pacmanlog_textview.get_buffer()
                self.pacmanlog_textview.set_buffer(self.buffer)

            pacmanlog_scrolledwindow.add(self.pacmanlog_textview)

            pacmanlog_grid.attach(pacmanlog_scrolledwindow, 0, 0, 1, 1)

            ivbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            ivbox.pack_start(btnPacmanLogOk, False, False, 0)

            pacmanlog_dialog.vbox.add(pacmanlog_grid)
            pacmanlog_dialog.vbox.add(ivbox)

            pacmanlog_dialog.show_all()

            thread_logtimer = "thread_startLogTimer"
            thread_logtimer_alive = False

            thread_logtimer_alive = fn.is_thread_alive(thread_logtimer)

            # a flag to indicate that the textview will need updating, used inside fn.startLogTimer
            self.start_logtimer = True

            if thread_logtimer_alive == False:
                th_logtimer = fn.threading.Thread(
                    name=thread_logtimer,
                    target=fn.startLogTimer,
                    args=(self,),
                    daemon=True,
                )
                th_logtimer.start()

        except Exception as e:
            fn.logger.error("Exception in on_pacman_log_clicked() : %s" % e)

    def onPacmanlogResponse(self, widget, dialog):
        dialog.destroy()
        # stop updating the textview
        self.start_logtimer = False


# ====================================================================
#                       MAIN
# ====================================================================


def signal_handler(sig, frame):
    fn.logger.info("Sofirem is closing.")
    if os.path.exists("/tmp/sofirem.lock"):
        os.unlink("/tmp/sofirem.lock")

    if os.path.exists("/tmp/sofirem.pid"):
        os.unlink("/tmp/sofirem.pid")
    Gtk.main_quit(0)


# These should be kept as it ensures that multiple installation instances can't be run concurrently.
if __name__ == "__main__":
    try:
        signal.signal(signal.SIGINT, signal_handler)

        if not os.path.isfile("/tmp/sofirem.lock"):
            with open("/tmp/sofirem.pid", "w") as f:
                f.write(str(os.getpid()))

            style_provider = Gtk.CssProvider()
            style_provider.load_from_path(base_dir + "/sofirem.css")

            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            w = Main()
            w.show_all()

            fn.logger.info("App Started")

            Gtk.main()
        else:
            md = Gtk.MessageDialog(
                parent=Main(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Lock File Found",
            )
            md.format_secondary_markup(
                "The lock file has been found. This indicates there is already an instance of <b>Sofirem</b> running.\n\
                Click 'Yes' to remove the lock file and try running again"
            )  # noqa

            result = md.run()
            md.destroy()

            if result in (Gtk.ResponseType.OK, Gtk.ResponseType.YES):
                pid = ""
                with open("/tmp/sofirem.pid", "r") as f:
                    line = f.read()
                    pid = line.rstrip().lstrip()

                if fn.checkIfProcessRunning(int(pid)):
                    # needs to be fixed - todo

                    # md2 = Gtk.MessageDialog(
                    #     parent=Main,
                    #     flags=0,
                    #     message_type=Gtk.MessageType.INFO,
                    #     buttons=Gtk.ButtonsType.OK,
                    #     title="Application Running!",
                    #     text="You first need to close the existing application",
                    # )
                    # md2.format_secondary_markup(
                    #     "You first need to close the existing application"
                    # )
                    # md2.run()
                    fn.logger.info("You first need to close the existing application")
                else:
                    os.unlink("/tmp/sofirem.lock")
    except Exception as e:
        fn.logger.error("Exception in __main__: %s" % e)
