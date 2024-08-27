#!/usr/bin/python3
# coding=utf-8

from gi.repository import Gtk, Gdk, Peas, GObject, RB, GLib
import os
import sys
import math

class TrayIcon(GObject.Object, Peas.Activatable):
    __gtype_name = 'TrayIcon'
    object = GObject.property(type=GObject.Object)

    def __init__(self):
        super().__init__()
        self.rhythmbox_icon = self.get_icon_path("tray_stopped.png")
        self.play_icon = self.get_icon_path("tray_playing.png")
        self.menu = None
        self.playing = False

    def get_icon_path(self, icon_name):
        return os.path.join(sys.path[0], icon_name)

    def position_menu_cb(self, menu, x, y=None, icon=None):
        try:
            return Gtk.StatusIcon.position_menu(self.menu, x, y, self.icon)
        except (AttributeError, TypeError):
            return Gtk.StatusIcon.position_menu(self.menu, self.icon)

    def show_popup_menu(self, icon, button, time, data=None):
        self.create_popup_menu()
        device = Gdk.Display.get_default().get_device_manager().get_client_pointer()
        self.menu.popup_for_device(device, None, None, self.position_menu_cb, self.icon, 3, time)

    def create_popup_menu(self):
        self.menu = Gtk.Menu()
        self.add_menu_items()
        self.menu.show_all()

    def add_menu_items(self):
        playpause_item = self.create_playpause_menu_item()
        next_item = self.create_menu_item("Next", "media-skip-forward-symbolic", self.next)
        prev_item = self.create_menu_item("Previous", "media-skip-backward-symbolic", self.previous)
        quit_item = self.create_menu_item("Close", "window-close-symbolic", self.quit)

        star_item = self.get_rating_menuitem()
        if star_item:
            self.menu.append(star_item)

        self.menu.append(playpause_item)
        self.menu.append(next_item)
        self.menu.append(prev_item)
        self.menu.append(quit_item)

    def create_menu_item(self, label, icon_name, callback):
        item = Gtk.ImageMenuItem(label)
        item.set_image(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU))
        item.connect("activate", callback)
        return item

    def create_playpause_menu_item(self):
        if self.playing:
            return self.create_menu_item("Pause", "media-playback-pause-symbolic", self.play)
        else:
            return self.create_menu_item("Play", "media-playback-start-symbolic", self.play)

    def get_rating_menuitem(self):
        menuitem_star = Gtk.MenuItem(self.get_stars_markup(0, 5))
        self.star_value = self.get_song_rating()
        label = menuitem_star.get_children()[0]
        label.set_markup(self.get_stars_markup(self.star_value, 5))

        menuitem_star.set_name('starMenu')

        menuitem_star.connect("motion_notify_event", self.on_star_mouseover)
        menuitem_star.connect("button_press_event", self.on_star_click)
        menuitem_star.connect("leave_notify_event", self.on_star_mouseout)

        if self.star_value >= 0:
            return menuitem_star
        else:
            return None

    def get_song_rating(self):
        current_entry = self.shell.props.shell_player.get_playing_entry()

        if current_entry:
            return int(current_entry.get_double(RB.RhythmDBPropType.RATING))
        else:
            return -1

    def on_star_click(self, widget, event):
        label = widget.get_children()[0]
        self.star_value = self.get_chosen_stars(label, event.x)
        self.set_song_rating(self.star_value)

    def set_song_rating(self, rating):
        current_entry = self.shell.props.shell_player.get_playing_entry()
        self.db.entry_set(current_entry, RB.RhythmDBPropType.RATING, rating)

    def get_chosen_stars(self, label, mouseX):
        star_width = int(label.get_layout().get_pixel_size()[0] / 5)
        chosen = math.ceil((mouseX - label.get_layout_offsets()[0]) / star_width)
        return max(0, min(5, chosen))

    def on_star_mouseout(self, widget, event):
        label = widget.get_children()[0]
        label.set_markup(self.get_stars_markup(self.star_value, 5))

    def on_star_mouseover(self, widget, event):
        label = widget.get_children()[0]
        label.set_markup(self.get_stars_markup(self.get_chosen_stars(label, event.x), 5))

    def get_stars_markup(self, filled_stars, total_stars):
        filled_stars = int(math.ceil(filled_stars or 0))
        star_string = '★' * filled_stars + '☆' * (total_stars - filled_stars)
        return f"<span size='x-large' foreground='#000000'>{star_string}</span>"

    def toggle_player_visibility(self, icon, event, data=None):
        if event.button == 1:
            if self.wind.get_visible():
                self.wind.hide()
            else:
                self.wind.show()
                self.wind.present()
        elif event.button == 2:
            self.player.do_next()

    def play(self, widget):
        try:
            self.player.playpause()
        except:
            self.player.playpause(True)

    def next(self, widget):
        self.player.do_next()

    def previous(self, widget):
        self.player.do_previous()

    def quit(self, widget):
        self.shell.quit()

    def hide_on_delete(self, widget, event):
        self.wind.hide()
        return True

    def on_playing_changed(self, player, playing):
        self.playing = playing
        if playing:
            self.icon.set_from_file(self.play_icon)
            current_entry = self.shell.props.shell_player.get_playing_entry()
            self.set_tooltip_text(f"{current_entry.get_string(RB.RhythmDBPropType.ARTIST)}\n{current_entry.get_string(RB.RhythmDBPropType.TITLE)}")
        else:
            self.icon.set_from_file(self.rhythmbox_icon)
            self.set_tooltip_text("Rhythmbox")

    def set_tooltip_text(self, message=""):
        self.icon.set_tooltip_text(message)

    def do_activate(self):
        self.shell = self.object
        self.wind = self.shell.get_property("window")
        self.player = self.shell.props.shell_player
        self.db = self.shell.props.db
        self.playing = False

        self.wind.connect("delete-event", self.hide_on_delete)
        self.create_popup_menu()

        self.icon = Gtk.StatusIcon()
        self.icon.set_from_file(self.rhythmbox_icon)
        self.icon.connect("scroll-event", self.on_scroll)
        self.icon.connect("popup-menu", self.show_popup_menu)
        self.icon.connect("button-press-event", self.toggle_player_visibility)
        self.player.connect("playing-changed", self.on_playing_changed)

        self.set_tooltip_text("Rhythmbox")

    def on_scroll(self, widget, event):
        vol = round(self.player.get_volume()[1], 1)
        if event.direction == Gdk.ScrollDirection.UP:
            vol += 0.1
        elif event.direction == Gdk.ScrollDirection.DOWN:
            vol -= 0.1

        self.player.set_volume(max(0, min(1, vol)))

    def do_deactivate(self):
        self.icon.set_visible(False)
        del self.icon
