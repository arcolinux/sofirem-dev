# This class is used to create a dialog window to list currently installed packages
import os
import gi
import Functions as fn
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")

base_dir = os.path.dirname(os.path.realpath(__file__))


class PackageListDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self)
        self.set_resizable(False)
        self.set_size_request(800, 700)
        self.set_modal(True)
        self.set_border_width(10)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))

        self.connect("delete-event", self.on_close)

        headerbar = Gtk.HeaderBar()
        headerbar.set_title("Showing installed packages")
        headerbar.set_show_close_button(True)

        self.set_titlebar(headerbar)

        grid_packageslst = Gtk.Grid()
        grid_packageslst.set_column_homogeneous(True)

        # get a list of installed packages on the system

        packages_lst = fn.get_installed_package_data()

        if len(packages_lst) > 0:
            self.set_title("Showing %s installed packages" % len(packages_lst))
            fn.logger.debug("List of installed packages obtained")

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
            scrolled_window.set_hexpand(True)

            grid_packageslst.attach(scrolled_window, 0, 0, 8, 10)

            lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding1.set_text("")

            grid_packageslst.attach_next_to(
                lbl_padding1, scrolled_window, Gtk.PositionType.BOTTOM, 1, 1
            )

            btn_dialog_export = Gtk.Button(label="Export")
            btn_dialog_export.connect(
                "clicked", self.on_dialog_export_clicked, packages_lst
            )
            btn_dialog_export.set_size_request(100, 30)
            # btn_dialog_export.set_halign(Gtk.Align.END)

            btn_dialog_export_close = Gtk.Button(label="Close")
            btn_dialog_export_close.connect("clicked", self.on_close, "delete-event")
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

            self.vbox.add(grid_packageslst)
            self.vbox.add(btn_grid)

    def on_close(self, dialog, event):
        self.hide()
        self.destroy()

    def on_dialog_export_clicked(self, dialog, packages_lst):
        try:
            filename = "%s/sofirem-export.txt" % fn.home

            with open(filename, "w", encoding="utf-8") as f:
                f.write(
                    "# Created by Sofirem on %s\n"
                    % fn.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                for package in packages_lst:
                    f.write("%s\n" % (package[0]))

            if os.path.exists(filename):
                fn.logger.info("Export completed")

                # fix permissions, file is owned by root
                fn.permissions(filename)

                fn.messageBox(
                    self,
                    "Package export complete",
                    "Package list exported to %s" % filename,
                )

            else:
                fn.logger.error("Export failed")
                fn.messageBox(
                    self,
                    "Package export failed",
                    "Failed to export package list to %s." % filename,
                )

        except Exception as e:
            fn.logger.error("Exception in on_dialog_export_clicked(): %s" % e)
