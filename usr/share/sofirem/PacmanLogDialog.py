# This class is used to create a dialog window to monitor the pacman log file
import os
import gi
import Functions as fn
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")

base_dir = os.path.dirname(os.path.realpath(__file__))


class PacmanLogDialog(Gtk.Dialog):
    def __init__(self, textview_pacmanlog):
        Gtk.Dialog.__init__(self)
        self.start_logtimer = True
        self.textview_pacmanlog = textview_pacmanlog
        pacmanlog_headerbar = Gtk.HeaderBar()

        pacmanlog_headerbar.set_show_close_button(True)

        self.set_titlebar(pacmanlog_headerbar)

        self.set_title("Pacman log file viewer")
        self.set_default_size(800, 600)
        self.set_resizable(False)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))
        self.connect("response", self.on_response)
        btnPacmanLogOk = Gtk.Button(label="OK")
        btnPacmanLogOk.connect("clicked", self.on_response, "response")

        btnPacmanLogOk.set_size_request(100, 30)

        grid_pacmanlog = Gtk.Grid()
        grid_pacmanlog.set_column_homogeneous(True)
        grid_pacmanlog.set_row_homogeneous(True)

        pacmanlog_scrolledwindow = Gtk.ScrolledWindow()

        lbl_padding_top1 = Gtk.Label(xalign=0)
        lbl_padding_top1.set_text("")

        lbl_padding_top2 = Gtk.Label(xalign=0)
        lbl_padding_top2.set_text("")

        lbl_btn_padding_right = Gtk.Label(xalign=0, yalign=0)
        lbl_btn_padding_right.set_name("lbl_btn_padding_right")

        lbl_btn_padding_right = Gtk.Label(xalign=0, yalign=0)
        lbl_btn_padding_right.set_name("lbl_btn_padding_right")

        pacmanlog_scrolledwindow.add(self.textview_pacmanlog)

        grid_pacmanlog.attach(pacmanlog_scrolledwindow, 0, 0, 1, 1)

        grid_btn = Gtk.Grid()

        grid_btn.attach(lbl_padding_top1, 0, 1, 1, 1)
        grid_btn.attach(lbl_padding_top2, 0, 2, 1, 1)
        grid_btn.attach_next_to(
            lbl_btn_padding_right, lbl_padding_top2, Gtk.PositionType.RIGHT, 1, 1
        )

        grid_btn.attach_next_to(
            btnPacmanLogOk, lbl_btn_padding_right, Gtk.PositionType.RIGHT, 1, 1
        )

        self.vbox.add(grid_pacmanlog)
        self.vbox.add(grid_btn)

    def on_response(self, dialog, response):
        # stop updating the textview
        fn.logger.debug("Closing pacman log monitoring dialog")
        self.start_logtimer = False
        self.hide()
        self.destroy()
