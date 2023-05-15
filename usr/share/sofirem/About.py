# This class stores static information about the app, and is displayed in the about dialog
import os
import gi

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")

base_dir = os.path.dirname(os.path.realpath(__file__))


class About(Gtk.AboutDialog):
    def __init__(self):
        app_name = "Sofirem"
        app_title = "About: Sofirem"
        app_main_message = "Sofirem"
        app_main_description = "Software Installer Remover"
        app_secondary_message = "Thanks for using Sofirem"
        app_secondary_description = "Report issues to make it even better"
        app_version = "version placeholder"
        app_support = "You can report issues on https://discord.gg/stBhS4taje"
        app_website = "https://arcolinux.com"
        app_authors = [
            "Erik Dubois",
            "Cameron Percival",
            "Fennec",
        ]

        Gtk.AboutDialog.__init__(self)

        self.set_title(app_title)
        self.set_program_name(app_name)
        self.set_name(app_main_message)
        self.set_version(app_version)
        self.set_comments(
            "%s\n%s\n%s" % (app_main_description, app_secondary_message, app_support)
        )
        self.set_website(app_website)
        self.set_website_label(app_website)
        self.set_authors(app_authors)
        self.connect("response", self.on_response)

        pixbuf = GdkPixbuf.Pixbuf().new_from_file_at_size(
            os.path.join(base_dir, "images/sofirem.png"), 45, 45
        )
        image = Gtk.Image().new_from_pixbuf(pixbuf)

        self.set_logo(pixbuf)

    def on_response(self, dialog, response):
        self.destroy()
