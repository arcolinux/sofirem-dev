# This class is used to create a dialog window showing progress of a package install/uninstall and general information
import os
import gi
import Functions as fn
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")

base_dir = os.path.dirname(os.path.realpath(__file__))


class ProgressDialog(Gtk.Dialog):
    def __init__(self, action, pkg, command):
        Gtk.Dialog.__init__(self)

        self.package_found = True
        # this gets package information using pacman -Sii or pacman -Qii depending on if this is an install / uninstall
        package_metadata = fn.get_package_information(self, pkg.name)

        if (
            type(package_metadata) is str
            and package_metadata.strip()
            == "error: package '%s' was not found" % pkg.name
        ):
            self.package_found = False
            fn.logger.warning(
                "The package %s was not found in any configured Pacman repositories"
                % pkg.name
            )
            fn.logger.warning("Package %s cannot continue" % action)

            fn.messageBox(
                self,
                "Pacman repository error: package '%s' was not found" % pkg.name,
                "<b>Sofirem cannot process the request</b>",
            )
        elif type(package_metadata) is dict:
            # package_progress_dialog = Gtk.Dialog(self)

            package_progress_dialog_headerbar = Gtk.HeaderBar()
            package_progress_dialog_headerbar.set_show_close_button(True)
            self.set_titlebar(package_progress_dialog_headerbar)

            self.connect("delete-event", package_progress_dialog_on_close, self, action)

            if action == "install":
                self.set_title("Sofirem - installing package %s" % pkg.name)

            elif action == "uninstall":
                self.set_title("Sofirem - removing package %s" % pkg.name)

            self.btn_package_progress_close = Gtk.Button(label="OK")
            self.btn_package_progress_close.connect(
                "clicked",
                on_package_progress_close_response,
                self,
            )
            self.btn_package_progress_close.set_sensitive(False)
            self.btn_package_progress_close.set_size_request(100, 30)

            self.set_resizable(False)
            self.set_size_request(750, 700)
            self.set_modal(True)
            self.set_border_width(10)
            self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
            self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))

            lbl_pacman_action_title = Gtk.Label(xalign=0, yalign=0)
            lbl_pacman_action_title.set_text("Running command:")

            lbl_pacman_action_value = Gtk.Label(xalign=0, yalign=0)
            lbl_pacman_action_value.set_markup("<b>%s</b>" % command)

            stack = Gtk.Stack()
            stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            stack.set_transition_duration(350)
            stack.set_hhomogeneous(False)
            stack.set_vhomogeneous(False)

            stack_switcher = Gtk.StackSwitcher()
            stack_switcher.set_orientation(Gtk.Orientation.HORIZONTAL)
            stack_switcher.set_stack(stack)
            stack_switcher.set_homogeneous(True)

            package_progress_grid = Gtk.Grid()

            self.infobar = Gtk.InfoBar()
            self.infobar.set_name("infobar_info")

            content = self.infobar.get_content_area()
            content.add(lbl_pacman_action_title)
            content.add(lbl_pacman_action_value)

            self.infobar.set_revealed(True)

            lbl_padding_header1 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding_header1.set_text("")

            package_progress_grid.attach(lbl_padding_header1, 0, 1, 1, 1)
            package_progress_grid.attach(self.infobar, 0, 2, 1, 1)

            package_progress_grid.set_property("can-focus", True)
            Gtk.Window.grab_focus(package_progress_grid)

            lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding1.set_text("")

            package_progress_grid.attach(lbl_padding1, 0, 3, 1, 1)

            package_progress_scrolled_window = Gtk.ScrolledWindow()
            self.package_progress_textview = Gtk.TextView()
            self.package_progress_textview.set_property("editable", False)
            self.package_progress_textview.set_property("monospace", True)
            self.package_progress_textview.set_border_width(10)
            self.package_progress_textview.set_vexpand(True)
            self.package_progress_textview.set_hexpand(True)
            buffer = self.package_progress_textview.get_buffer()
            self.package_progress_textview.set_buffer(buffer)

            package_progress_scrolled_window.add(self.package_progress_textview)
            package_progress_grid.attach(package_progress_scrolled_window, 0, 4, 1, 1)

            package_progress_btn_grid = Gtk.Grid()

            lbl_padding_btn = Gtk.Label(xalign=0, yalign=0)
            lbl_padding_btn.set_name("lbl_btn_padding_right")

            lbl_padding_btn_top = Gtk.Label(xalign=0, yalign=0)
            lbl_padding_btn_top.set_text("")

            package_progress_btn_grid.attach(lbl_padding_btn_top, 0, 1, 1, 1)

            package_progress_btn_grid.attach(lbl_padding_btn, 0, 2, 5, 1)

            package_progress_btn_grid.attach_next_to(
                self.btn_package_progress_close,
                lbl_padding_btn,
                Gtk.PositionType.RIGHT,
                1,
                1,
            )

            stack.add_titled(package_progress_grid, "Progress", "Package Progress")

            # package information
            box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

            listbox = Gtk.ListBox()
            listbox.set_selection_mode(Gtk.SelectionMode.NONE)
            box_outer.pack_start(listbox, True, True, 0)

            # package name
            row_package_title = Gtk.ListBoxRow()
            vbox_package_title = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=0
            )
            row_package_title.add(vbox_package_title)
            lbl_package_name_title = Gtk.Label(xalign=0)
            lbl_package_name_title.set_markup("<b>Package Name</b>")

            lbl_package_name_value = Gtk.Label(xalign=0)
            lbl_package_name_value.set_text(package_metadata["name"])
            vbox_package_title.pack_start(lbl_package_name_title, True, True, 0)
            vbox_package_title.pack_start(lbl_package_name_value, True, True, 0)

            listbox.add(row_package_title)

            # repository

            row_package_repo = Gtk.ListBoxRow()
            vbox_package_repo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            row_package_repo.add(vbox_package_repo)
            lbl_package_repo_title = Gtk.Label(xalign=0)
            lbl_package_repo_title.set_markup("<b>Repository</b>")

            lbl_package_repo_value = Gtk.Label(xalign=0)
            lbl_package_repo_value.set_text(package_metadata["repository"])
            vbox_package_repo.pack_start(lbl_package_repo_title, True, True, 0)
            vbox_package_repo.pack_start(lbl_package_repo_value, True, True, 0)

            listbox.add(row_package_repo)

            # description

            row_package_description = Gtk.ListBoxRow()
            vbox_package_description = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=0
            )
            row_package_description.add(vbox_package_description)
            lbl_package_description_title = Gtk.Label(xalign=0)
            lbl_package_description_title.set_markup("<b>Description</b>")

            lbl_package_description_value = Gtk.Label(xalign=0)
            lbl_package_description_value.set_text(package_metadata["description"])
            vbox_package_description.pack_start(
                lbl_package_description_title, True, True, 0
            )
            vbox_package_description.pack_start(
                lbl_package_description_value, True, True, 0
            )

            listbox.add(row_package_description)

            # arch

            row_package_arch = Gtk.ListBoxRow()
            vbox_package_arch = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            row_package_arch.add(vbox_package_arch)
            lbl_package_arch_title = Gtk.Label(xalign=0)
            lbl_package_arch_title.set_markup("<b>Architecture</b>")

            lbl_package_arch_value = Gtk.Label(xalign=0)
            lbl_package_arch_value.set_text(package_metadata["arch"])
            vbox_package_arch.pack_start(lbl_package_arch_title, True, True, 0)
            vbox_package_arch.pack_start(lbl_package_arch_value, True, True, 0)

            listbox.add(row_package_arch)

            # url

            row_package_url = Gtk.ListBoxRow()
            vbox_package_url = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            row_package_url.add(vbox_package_url)
            lbl_package_url_title = Gtk.Label(xalign=0)
            lbl_package_url_title.set_markup("<b>URL</b>")

            lbl_package_url_value = Gtk.Label(xalign=0)
            lbl_package_url_value.set_markup(
                "<a href=''>%s</a>" % package_metadata["url"]
            )
            vbox_package_url.pack_start(lbl_package_url_title, True, True, 0)
            vbox_package_url.pack_start(lbl_package_url_value, True, True, 0)

            listbox.add(row_package_url)

            # download size

            row_package_size = Gtk.ListBoxRow()
            vbox_package_size = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            row_package_size.add(vbox_package_size)
            lbl_package_size_title = Gtk.Label(xalign=0)
            lbl_package_size_title.set_markup("<b>Download size</b>")

            lbl_package_size_value = Gtk.Label(xalign=0)
            lbl_package_size_value.set_text(package_metadata["download_size"])
            vbox_package_size.pack_start(lbl_package_size_title, True, True, 0)
            vbox_package_size.pack_start(lbl_package_size_value, True, True, 0)

            listbox.add(row_package_size)

            # installed size

            row_package_installed_size = Gtk.ListBoxRow()
            vbox_package_installed_size = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=0
            )
            row_package_installed_size.add(vbox_package_installed_size)
            lbl_package_installed_size_title = Gtk.Label(xalign=0)
            lbl_package_installed_size_title.set_markup("<b>Installed size</b>")

            lbl_package_installed_size_value = Gtk.Label(xalign=0)
            lbl_package_installed_size_value.set_text(
                package_metadata["installed_size"]
            )
            vbox_package_installed_size.pack_start(
                lbl_package_installed_size_title, True, True, 0
            )
            vbox_package_installed_size.pack_start(
                lbl_package_installed_size_value, True, True, 0
            )

            listbox.add(row_package_installed_size)

            # build date

            row_package_build_date = Gtk.ListBoxRow()
            vbox_package_build_date = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=0
            )
            row_package_build_date.add(vbox_package_build_date)
            lbl_package_build_date_title = Gtk.Label(xalign=0)
            lbl_package_build_date_title.set_markup("<b>Build date</b>")

            lbl_package_build_date_value = Gtk.Label(xalign=0)
            lbl_package_build_date_value.set_text(package_metadata["build_date"])
            vbox_package_build_date.pack_start(
                lbl_package_build_date_title, True, True, 0
            )
            vbox_package_build_date.pack_start(
                lbl_package_build_date_value, True, True, 0
            )

            listbox.add(row_package_build_date)

            # packager

            row_package_maintainer = Gtk.ListBoxRow()
            vbox_package_maintainer = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=0
            )
            row_package_maintainer.add(vbox_package_maintainer)
            lbl_package_maintainer_title = Gtk.Label(xalign=0)
            lbl_package_maintainer_title.set_markup("<b>Packager</b>")

            lbl_package_maintainer_value = Gtk.Label(xalign=0)
            lbl_package_maintainer_value.set_text(package_metadata["packager"])
            vbox_package_maintainer.pack_start(
                lbl_package_maintainer_title, True, True, 0
            )
            vbox_package_maintainer.pack_start(
                lbl_package_maintainer_value, True, True, 0
            )

            listbox.add(row_package_maintainer)

            # depends on

            row_package_depends_on = Gtk.ListBoxRow()
            vbox_package_depends_on = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=0
            )
            row_package_depends_on.add(vbox_package_depends_on)
            lbl_package_depends_on_title = Gtk.Label(xalign=0)
            lbl_package_depends_on_title.set_markup("<b>Depends on</b>")

            if len(package_metadata["depends_on"]) > 0:
                treestore_depends = Gtk.TreeStore(str, str)

                for item in package_metadata["depends_on"]:
                    treestore_depends.append(None, list(item))

                treeview_depends = Gtk.TreeView(model=treestore_depends)

                renderer = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn("Package", renderer, text=0)

                treeview_depends.append_column(column)

                vbox_package_depends_on.pack_start(
                    lbl_package_depends_on_title, True, True, 0
                )

                vbox_package_depends_on.pack_start(treeview_depends, True, True, 0)

            else:
                lbl_package_depends_value = Gtk.Label(xalign=0, yalign=0)
                lbl_package_depends_value.set_text("None")

                vbox_package_depends_on.pack_start(
                    lbl_package_depends_on_title, True, True, 0
                )

                vbox_package_depends_on.pack_start(
                    lbl_package_depends_value, True, True, 0
                )

            listbox.add(row_package_depends_on)

            # conflicts with

            row_package_conflicts_with = Gtk.ListBoxRow()
            vbox_package_conflicts_with = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=0
            )
            row_package_conflicts_with.add(vbox_package_conflicts_with)
            lbl_package_conflicts_with_title = Gtk.Label(xalign=0)
            lbl_package_conflicts_with_title.set_markup("<b>Conflicts with</b>")

            if len(package_metadata["conflicts_with"]) > 0:
                treestore_conflicts = Gtk.TreeStore(str, str)

                for item in package_metadata["conflicts_with"]:
                    treestore_conflicts.append(None, list(item))

                treeview_conflicts = Gtk.TreeView(model=treestore_conflicts)

                renderer = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn("Package", renderer, text=0)

                treeview_conflicts.append_column(column)

                vbox_package_conflicts_with.pack_start(
                    lbl_package_conflicts_with_title, True, True, 0
                )

                vbox_package_conflicts_with.pack_start(
                    treeview_conflicts, True, True, 0
                )

            else:
                lbl_package_conflicts_with_value = Gtk.Label(xalign=0, yalign=0)
                lbl_package_conflicts_with_value.set_text("None")

                vbox_package_conflicts_with.pack_start(
                    lbl_package_conflicts_with_title, True, True, 0
                )

                vbox_package_conflicts_with.pack_start(
                    lbl_package_conflicts_with_value, True, True, 0
                )

            listbox.add(row_package_conflicts_with)

            package_metadata_scrolled_window = Gtk.ScrolledWindow()

            package_metadata_scrolled_window.add(box_outer)

            stack.add_titled(
                package_metadata_scrolled_window, "Package Information", "Information"
            )

            self.vbox.add(stack_switcher)
            self.vbox.add(stack)
            self.vbox.add(package_progress_btn_grid)


def on_package_progress_close_response(self, widget):
    self.pkg_dialog_closed = True
    fn.logger.debug("Closing package progress dialog")
    widget.hide()
    widget.destroy()


def package_progress_dialog_on_close(widget, data, self, action):
    self.pkg_dialog_closed = True
    fn.logger.debug("Closing package progress dialog")
    widget.hide()
    widget.destroy()
