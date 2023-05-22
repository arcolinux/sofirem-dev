# This class is used to create a dialog window to monitor the pacman log file
import os
import gi
import Functions as fn
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")

base_dir = os.path.dirname(os.path.realpath(__file__))


class PacmanLogDialog(Gtk.Dialog):
    def __init__(self, textview_pacmanlog, btn_pacmanlog):
        Gtk.Dialog.__init__(self)
        self.start_logtimer = True
        self.textview_pacmanlog = textview_pacmanlog
        self.btn_pacmanlog = btn_pacmanlog
        headerbar = Gtk.HeaderBar()

        headerbar.set_show_close_button(True)

        self.set_titlebar(headerbar)

        self.set_title("Pacman log file viewer")
        self.set_default_size(800, 600)
        self.set_resizable(False)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))
        self.connect("response", self.on_response)
        btn_pacmanlog_ok = Gtk.Button(label="OK")
        btn_pacmanlog_ok.connect("clicked", self.on_response, "response")

        btn_pacmanlog_ok.set_size_request(100, 30)
        btn_pacmanlog_ok.set_halign(Gtk.Align.END)

        grid_pacmanlog = Gtk.Grid()
        # grid_pacmanlog.set_column_homogeneous(True)
        # grid_pacmanlog.set_row_homogeneous(True)

        pacmanlog_scrolledwindow = Gtk.ScrolledWindow()

        pacmanlog_scrolledwindow.add(self.textview_pacmanlog)

        lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding1.set_text(" ")

        grid_pacmanlog.attach(pacmanlog_scrolledwindow, 0, 1, 1, 1)
        grid_pacmanlog.attach(lbl_padding1, 0, 2, 1, 1)

        grid_btn = Gtk.Grid()
        grid_btn.attach(btn_pacmanlog_ok, 0, 1, 1, 1)

        lbl_padding2 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding2.set_text(" ")

        grid_btn.attach_next_to(
            lbl_padding2, btn_pacmanlog_ok, Gtk.PositionType.RIGHT, 1, 1
        )

        grid_btn.set_halign(Gtk.Align.END)

        vbox_close = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_close.pack_start(grid_btn, True, True, 1)

        self.vbox.add(grid_pacmanlog)
        self.vbox.add(vbox_close)

    def on_response(self, dialog, response):
        # stop updating the textview
        fn.logger.debug("Closing pacman log monitoring dialog")
        self.start_logtimer = False
        self.btn_pacmanlog.set_sensitive(True)
        self.hide()
        self.destroy()
