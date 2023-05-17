# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================


# ============Functions============
import Functions as fn
import App_Frame_GUI
from multiprocessing import cpu_count
from queue import Queue
from threading import Thread

base_dir = fn.os.path.dirname(fn.os.path.realpath(__file__))


class GUI_Worker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # pull what we need from the queue so we can process properly.
            items = self.queue.get()
            try:
                # make sure we have the required number of items on the queue
                if items is not None:
                    # self, Gtk, vboxStack1, category, package_file = items

                    self, Gtk, vboxStack1, category, packages = items

                    App_Frame_GUI.GUI(
                        self,
                        Gtk,
                        vboxStack1,
                        category,
                        packages,
                    )

            except Exception as e:
                fn.logger.error("Exception in GUI_Worker(): %s" % e)
            finally:
                if items is None:
                    fn.logger.debug("Stopping GUI Worker thread")
                    self.queue.task_done()
                    return False
                self.queue.task_done()


def setup_gui_search(
    self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango, search_results, search_term
):
    try:
        # remove previous vbox
        if self.search_activated == False:
            self.remove(self.vbox)
        else:
            self.remove(self.vbox_search)

        # lets quickly create the latest installed list.
        fn.get_current_installed()

        # =======================================================
        #                       HeaderBar
        # =======================================================

        setup_headerbar(self, Gtk)

        # =======================================================
        #                       App Notifications
        # =======================================================

        hbox0 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.notification_revealer = Gtk.Revealer()
        self.notification_revealer.set_reveal_child(False)

        self.notification_label = Gtk.Label()

        pb_panel = GdkPixbuf.Pixbuf().new_from_file(base_dir + "/images/panel.png")
        panel = Gtk.Image().new_from_pixbuf(pb_panel)

        overlayFrame = Gtk.Overlay()
        overlayFrame.add(panel)
        overlayFrame.add_overlay(self.notification_label)

        self.notification_revealer.add(overlayFrame)

        hbox0.pack_start(self.notification_revealer, True, False, 0)

        # ==========================================================
        #                       CONTAINER
        # ==========================================================

        self.vbox_search = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.vbox_search.pack_start(hbox, True, True, 0)
        self.add(self.vbox_search)

        # ==========================================================
        #                    PREP WORK
        # ==========================================================

        # This section sets up the tabs, and the array for dealing with the tab content

        # ==========================================================
        #                       GENERATE STACK
        # ==========================================================
        stack = Gtk.Stack()
        # stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        stack.set_transition_duration(350)

        vboxStack = []
        stack_item = 0

        # Max Threads
        """
            Fatal Python error: Segmentation fault
            This error happens randomly, due to the for loop iteration on the cpu_count
            old code: for x in range(cpu_count()):
        """

        # spawn only 1 GUI_Worker threads, as any number greater causes a Segmentation fault

        search_worker = GUI_Worker(self.queue)
        search_worker.name = "thread_GUI_search_worker"
        # Set the worker to be True to allow processing, and avoid Blocking
        search_worker.daemon = True
        search_worker.start()

        # This code section might look a little weird. It is because it was
        # derived from another function before this version was required.

        for category in search_results:
            # NOTE: IF the yaml file name standard changes, be sure to update this, or weirdness will follow.

            # subcategory = search_results[category][0].subcategory
            vboxStack.append(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10))
            stack.add_titled(
                vboxStack[stack_item], str("stack" + str(len(vboxStack))), category
            )

            # subcategory_desc = search_results[category][0].subcategory_description
            search_res_lst = search_results[category]

            # Multithreading!

            self.queue.put(
                (
                    self,
                    Gtk,
                    vboxStack[stack_item],
                    category,
                    search_res_lst,
                )
            )

            stack_item += 1

        # send a signal that no further items are to be put on the queue
        self.queue.put(None)
        # safety to ensure that we finish threading before we continue on.
        self.queue.join()
        fn.logger.debug("GUI Worker thread completed")

        stack_switcher = Gtk.StackSidebar()
        stack_switcher.set_name("sidebar")
        stack_switcher.set_stack(stack)

        # =====================================================
        #                       LOGO
        # =====================================================

        ivbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        pixbuf = GdkPixbuf.Pixbuf().new_from_file_at_size(
            os.path.join(base_dir, "images/sofirem.png"), 45, 45
        )
        image = Gtk.Image().new_from_pixbuf(pixbuf)

        # remove the focus on startup from search entry
        ivbox.set_property("can-focus", True)
        Gtk.Window.grab_focus(ivbox)

        # =====================================================
        #               RECACHE BUTTON
        # =====================================================

        btnReCache = Gtk.Button(label="Recache Applications")
        btnReCache.connect("clicked", self.recache_clicked)
        # btnReCache.set_property("has-tooltip", True)
        # btnReCache.connect("query-tooltip", self.tooltip_callback,
        #           "Refresh the application cache")

        # =====================================================
        #                   REPOS
        # =====================================================

        if not (
            fn.check_package_installed("arcolinux-keyring")
            or fn.check_package_installed("arcolinux-mirrorlist-git")
        ):
            self.btnRepos = Gtk.Button(label="Add ArcoLinux Repo")
            self.btnRepos._value = 1
        else:
            self.btnRepos = Gtk.Button(label="Remove ArcoLinux Repo")
            self.btnRepos._value = 2

        self.btnRepos.set_size_request(100, 30)
        self.btnRepos.connect("clicked", self.on_repos_clicked)

        # =====================================================
        #               QUIT BUTTON
        # =====================================================

        # btnQuitSofi = Gtk.Button(label="Quit")
        # btnQuitSofi.set_size_request(100, 30)
        # btnQuitSofi.connect("clicked", self.on_close, "delete-event")

        # =====================================================
        #               SEARCH BOX
        # =====================================================

        self.searchEntry = Gtk.SearchEntry()
        self.searchEntry.set_text(search_term)
        self.searchEntry.connect("activate", self.on_search_activated)
        self.searchEntry.connect("icon-release", self.on_search_cleared)

        ivSearchbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # =====================================================
        #                      PACKS
        # =====================================================

        # hbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        # hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        # hbox3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        # hbox3.pack_start(btnReCache, False, False, 0)

        ivSearchbox.pack_start(self.searchEntry, False, False, 0)

        ivbox.pack_start(image, False, False, 0)
        ivbox.pack_start(ivSearchbox, False, False, 0)
        ivbox.pack_start(stack_switcher, True, True, 0)

        # ivbox.pack_start(btnReCache, False, False, 0)
        ivbox.pack_start(self.btnRepos, False, False, 0)
        # ivbox.pack_start(btnQuitSofi, False, False, 0)

        vbox1.pack_start(hbox0, False, False, 0)
        vbox1.pack_start(stack, True, True, 0)

        hbox.pack_start(ivbox, False, True, 0)
        hbox.pack_start(vbox1, True, True, 0)

        stack.set_hhomogeneous(False)
        stack.set_vhomogeneous(False)

        self.show_all()

    except Exception as err:
        fn.logger.error("Exception in GUISearch(): %s" % err)


def setup_gui(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango):  # noqa
    try:
        # reset back to main box
        if self.search_activated:
            # remove the search vbox
            self.remove(self.vbox_search)
            self.show_all()

        # lets quickly create the latest installed list.
        fn.get_current_installed()

        # =======================================================
        #                       HeaderBar
        # =======================================================

        setup_headerbar(self, Gtk)

        # =======================================================
        #                       App Notifications
        # =======================================================

        hbox0 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.notification_revealer = Gtk.Revealer()
        self.notification_revealer.set_reveal_child(False)

        self.notification_label = Gtk.Label()

        pb_panel = GdkPixbuf.Pixbuf().new_from_file(base_dir + "/images/panel.png")
        panel = Gtk.Image().new_from_pixbuf(pb_panel)

        overlayFrame = Gtk.Overlay()
        overlayFrame.add(panel)
        overlayFrame.add_overlay(self.notification_label)

        self.notification_revealer.add(overlayFrame)

        hbox0.pack_start(self.notification_revealer, True, False, 0)

        # ==========================================================
        #                       CONTAINER
        # ==========================================================

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.vbox.pack_start(hbox, True, True, 0)
        self.add(self.vbox)

        # ==========================================================
        #                    PREP WORK
        # ==========================================================

        # This section sets up the tabs, and the array for dealing with the tab content
        """
        yaml_files_unsorted = []
        path = base_dir + "/yaml/"
        for file in os.listdir(path):
            if file.endswith(".yaml"):
                yaml_files_unsorted.append(file)
            else:
                print(
                    "Unsupported configuration file type. Please contact Arcolinux Support."
                )
        # Need to sort the list (Or do we? I choose to)
        yaml_files = sorted(yaml_files_unsorted)
        """

        # Check github for updated files
        # fn.check_github(yaml_files)
        # ==========================================================
        #                       GENERATE STACK
        # ==========================================================
        stack = Gtk.Stack()
        # stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        stack.set_transition_duration(350)

        vboxStack = []
        stack_item = 0

        # Max Threads
        """
            Fatal Python error: Segmentation fault
            This error happens randomly, due to the for loop iteration on the cpu_count
            old code: for x in range(cpu_count()):
        """

        # spawn only 1 GUI_Worker threads, as any number greater causes a Segmentation fault

        worker = GUI_Worker(self.queue)
        worker.name = "thread_GUI_Worker"
        # Set the worker to be True to allow processing, and avoid Blocking
        worker.daemon = True
        worker.start()

        for category in self.packages:
            # NOTE: IF the yaml file name standard changes, be sure to update this, or weirdness will follow.

            # this is the side stack listing all categories
            vboxStack.append(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10))
            stack.add_titled(
                vboxStack[stack_item], str("stack" + str(len(vboxStack))), category
            )

            packages_lst = self.packages[category]

            # Multithreading!
            self.queue.put(
                (
                    self,
                    Gtk,
                    vboxStack[stack_item],
                    category,
                    packages_lst,
                )
            )
            stack_item += 1

        # send a signal that no further items are to be put on the queue
        self.queue.put(None)
        # safety to ensure that we finish threading before we continue on.

        self.queue.join()
        fn.logger.debug("GUI Worker thread completed")

        stack_switcher = Gtk.StackSidebar()
        stack_switcher.set_name("sidebar")
        stack_switcher.set_stack(stack)

        # =====================================================
        #                       LOGO
        # =====================================================

        ivbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        pixbuf = GdkPixbuf.Pixbuf().new_from_file_at_size(
            os.path.join(base_dir, "images/sofirem.png"), 45, 45
        )
        image = Gtk.Image().new_from_pixbuf(pixbuf)

        # remove the focus on startup from search entry
        ivbox.set_property("can-focus", True)
        Gtk.Window.grab_focus(ivbox)

        # =====================================================
        #               RECACHE BUTTON
        # =====================================================

        btnReCache = Gtk.Button(label="Recache Applications")
        btnReCache.connect("clicked", self.recache_clicked)
        # btnReCache.set_property("has-tooltip", True)
        # btnReCache.connect("query-tooltip", self.tooltip_callback,
        #           "Refresh the application cache")

        # =====================================================
        #                   REPOS
        # =====================================================

        # =====================================================
        #               QUIT BUTTON
        # =====================================================
        # btnQuitSofi = Gtk.Button(label="Quit")
        # btnQuitSofi.set_size_request(100, 30)
        # btnQuitSofi.connect("clicked", self.on_close, "delete-event")

        # =====================================================
        #               SEARCH BOX
        # =====================================================
        self.searchEntry = Gtk.SearchEntry()
        self.searchEntry.set_placeholder_text("Search...")
        self.searchEntry.connect("activate", self.on_search_activated)
        self.searchEntry.connect("icon-release", self.on_search_cleared)

        ivSearchbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        ivSearchbox.pack_start(self.searchEntry, False, False, 0)

        ivbox.pack_start(image, False, False, 0)
        ivbox.pack_start(ivSearchbox, False, False, 0)
        ivbox.pack_start(stack_switcher, True, True, 0)

        # leaving cache button out
        # ivbox.pack_start(btnReCache, False, False, 0)
        # ivbox.pack_start(self.btnRepos, False, False, 0)
        # ivbox.pack_start(btnQuitSofi, False, False, 0)

        vbox1.pack_start(hbox0, False, False, 0)
        vbox1.pack_start(stack, True, True, 0)

        hbox.pack_start(ivbox, False, True, 0)
        hbox.pack_start(vbox1, True, True, 0)

        stack.set_hhomogeneous(False)
        stack.set_vhomogeneous(False)

        if self.search_activated:
            self.show_all()

    except Exception as e:
        fn.logger.error("Exception in GUI(): %s" % e)


def setup_headerbar(self, Gtk):
    try:
        header_bar_title = "Sofirem"
        headerbar = Gtk.HeaderBar()
        headerbar.set_title(header_bar_title)
        headerbar.set_show_close_button(True)

        self.set_titlebar(headerbar)

        toolbuttonSettings = Gtk.ToolButton()
        toolbuttonSettings.set_icon_name("open-menu-symbolic.symbolic")
        # toolbuttonSettings.set_icon_name(Gtk.STOCK_PREFERENCES)
        toolbuttonSettings.connect("clicked", self.on_settings_clicked)

        headerbar.pack_end(toolbuttonSettings)

        self.popover = Gtk.PopoverMenu.new()
        self.popover.set_relative_to(toolbuttonSettings)

        vbox = Gtk.Box(spacing=1, orientation=Gtk.Orientation.VERTICAL)
        vbox.set_border_width(10)

        # switch to display package versions
        switchSettingsVersion = Gtk.Switch()
        switchSettingsVersion.set_halign(Gtk.Align(1))

        # button to open the pacman log monitoring dialog
        btnPacmanLog = Gtk.Button(label="Open Pacman Log File")
        btnPacmanLog.connect("clicked", self.on_pacman_log_clicked)
        btnPacmanLog.set_size_request(100, 30)

        # button to export list of installed packages to disk
        btn_packages_export = Gtk.Button(label="Show Installed Packages")
        btn_packages_export.connect("clicked", self.on_packages_export_clicked)
        btn_packages_export.set_size_request(100, 30)

        # quit button

        btn_quit_sofi = Gtk.Button(label="Quit")
        btn_quit_sofi.set_size_request(100, 30)
        btn_quit_sofi.connect("clicked", self.on_close, "delete-event")

        # button to show about dialog
        btn_about_app = Gtk.Button(label="About")
        btn_about_app.connect("clicked", self.on_about_app_clicked)
        btn_about_app.set_size_request(100, 30)

        if self.display_versions == True:
            switchSettingsVersion.set_active(True)
        else:
            switchSettingsVersion.set_active(False)

        switchSettingsVersion.connect("notify::active", self.version_toggle)

        if not (
            fn.check_package_installed("arcolinux-keyring")
            or fn.check_package_installed("arcolinux-mirrorlist-git")
        ):
            self.btnRepos = Gtk.Button(label="Add ArcoLinux Repos")
            self.btnRepos._value = 1
        else:
            self.btnRepos = Gtk.Button(label="Remove ArcoLinux Repos")
            self.btnRepos._value = 2

        self.btnRepos.set_size_request(100, 30)
        self.btnRepos.connect("clicked", self.on_repos_clicked)

        lblSettingsVersion = Gtk.Label(xalign=0, yalign=0)
        lblSettingsVersion.set_text("Display package version")

        lblSettingsPadding1 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPadding1.set_text("    ")

        lblSettingsPadding2 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPadding2.set_text("    ")

        gridSettings = Gtk.Grid()

        # attach_next_to(new,existing)
        # attach (self, child:Gtk.Widget, left:int, top:int, width:int, height:int)
        gridSettings.attach(lblSettingsPadding1, 0, 0, 1, 1)

        gridSettings.attach_next_to(
            lblSettingsVersion, lblSettingsPadding1, Gtk.PositionType.RIGHT, 1, 1
        )

        gridSettings.attach_next_to(
            lblSettingsPadding2, lblSettingsVersion, Gtk.PositionType.RIGHT, 1, 1
        )

        gridSettings.attach_next_to(
            switchSettingsVersion, lblSettingsPadding2, Gtk.PositionType.RIGHT, 1, 1
        )

        # add the repos button

        lblSettingsPaddingRow1 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPaddingRow1.set_text("    ")

        gridSettings.attach(lblSettingsPaddingRow1, 0, 1, 1, 1)

        lblSettingsPadding3 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPadding3.set_text("    ")

        gridSettings.attach(lblSettingsPadding3, 0, 2, 1, 1)

        gridSettings.attach_next_to(
            self.btnRepos, lblSettingsPadding3, Gtk.PositionType.RIGHT, 20, 1
        )

        # add the pacman log button
        lblSettingsPaddingRow2 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPaddingRow2.set_text("    ")

        gridSettings.attach(lblSettingsPaddingRow2, 0, 3, 1, 1)

        lblSettingsPadding4 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPadding4.set_text("    ")

        gridSettings.attach(lblSettingsPadding4, 0, 4, 1, 1)

        gridSettings.attach_next_to(
            btnPacmanLog, lblSettingsPadding4, Gtk.PositionType.RIGHT, 20, 1
        )

        # add export package list button
        lblSettingsPaddingRow3 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPaddingRow3.set_text("    ")

        gridSettings.attach(lblSettingsPaddingRow3, 0, 5, 1, 1)

        lblSettingsPadding5 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPadding5.set_text("    ")

        gridSettings.attach(lblSettingsPadding5, 0, 6, 1, 1)

        gridSettings.attach_next_to(
            btn_packages_export, lblSettingsPadding5, Gtk.PositionType.RIGHT, 20, 1
        )

        # add about dialog button
        lblSettingsPaddingRow4 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPaddingRow4.set_text("    ")

        gridSettings.attach(lblSettingsPaddingRow4, 0, 7, 1, 1)

        lblSettingsPadding6 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPadding6.set_text("    ")

        gridSettings.attach(lblSettingsPadding6, 0, 8, 1, 1)

        gridSettings.attach_next_to(
            btn_about_app, lblSettingsPadding6, Gtk.PositionType.RIGHT, 20, 1
        )

        # add quit button

        lblSettingsPaddingRow5 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPaddingRow5.set_text("    ")

        gridSettings.attach(lblSettingsPaddingRow5, 0, 9, 1, 1)

        lblSettingsPadding7 = Gtk.Label(xalign=0, yalign=0)
        lblSettingsPadding7.set_text("    ")

        gridSettings.attach(lblSettingsPadding7, 0, 10, 1, 1)

        gridSettings.attach_next_to(
            btn_quit_sofi, lblSettingsPadding7, Gtk.PositionType.RIGHT, 20, 1
        )

        vbox.pack_start(gridSettings, True, True, 0)

        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
    except Exception as e:
        fn.logger.error("Exception in setup_headerbar(): %s" % e)
