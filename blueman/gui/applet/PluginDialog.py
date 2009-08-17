# Copyright (C) 2008 Valmantas Paliksa <walmis at balticum-tv dot lt>
# Copyright (C) 2008 Tadas Dailyda <tadas at dailyda dot com>
#
# Licensed under the GNU General Public License Version 3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 

import gtk
from blueman.Constants import *

from blueman.Functions import *
from blueman.Functions import _

from blueman.gui.GenericList import GenericList
import weakref

class PluginDialog(gtk.Dialog):
	def __init__(self, applet):
		gtk.Dialog.__init__(self, buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
		
		self.applet = applet
		
		self.Builder = gtk.Builder()
		self.Builder.set_translation_domain("blueman")
		self.Builder.add_from_file(UI_PATH +"/applet-plugins-widget.ui")
		
		self.set_title(_("Plugins"))
		self.props.icon_name = "blueman"
		
		self.description = self.Builder.get_object("description")
		self.description.props.wrap = True
		
		self.icon = self.Builder.get_object("icon")
		self.author = self.Builder.get_object("author")
		self.depends_hdr = self.Builder.get_object("depends_hdr")
		self.depends_txt = self.Builder.get_object("depends_txt")
		self.plugin_name = self.Builder.get_object("name")
	
		widget = self.Builder.get_object("all")
		
		ref = weakref.ref(self)
		
		self.vbox.pack_start(widget)
		
		cr = gtk.CellRendererToggle()
		cr.connect("toggled", lambda *args: ref() and ref().on_toggled(*args))
		
		data = [
			["active", bool, cr, {"active":0, "activatable":1, "visible":1}, None],
			["activatable", bool],
			["icon", str, gtk.CellRendererPixbuf(), {"icon-name":2}, None],
			
			#device caption
			["name", str, gtk.CellRendererText(), {"markup":3}, None, {"expand": True}]
		]
		
		
		self.list = GenericList(data)
		self.list.selection.connect("changed", lambda *args: ref() and ref().on_selection_changed(*args))
		
		self.list.props.headers_visible = False
		self.list.show()
		
		self.props.border_width = 6
		self.resize(490, 380)
		
		self.Builder.get_object("viewport").add(self.list)
		
		self.populate()
		
		self.sig_a = self.applet.Plugins.connect("plugin-loaded", self.plugin_state_changed, True)
		self.sig_b = self.applet.Plugins.connect("plugin-unloaded", self.plugin_state_changed, False)
		self.connect("response", self.on_response)
		
		self.list.set_cursor(0)
		
	def on_response(self, dialog, resp):
		self.applet.Plugins.disconnect(self.sig_a)
		self.applet.Plugins.disconnect(self.sig_b)
		
	def on_selection_changed(self, selection):
		model, iter = selection.get_selected()
		
		name = self.list.get(iter, "name")["name"]
		cls = self.applet.Plugins.GetClasses()[name]
		self.plugin_name.props.label = "<b>" + name + "</b>"
		self.icon.props.icon_name = cls.__icon__
		self.author.props.label = cls.__author__ or _("Unspecified")
		self.description.props.label = cls.__description__ or _("Unspecified")
		
		if cls.__depends__ != []:
			self.depends_hdr.props.visible = True
			self.depends_txt.props.visible = True
			self.depends_txt.props.label = ", ".join(cls.__depends__)
		else:
			self.depends_hdr.props.visible = False
			self.depends_txt.props.visible = False
		
		
	def populate(self):
		classes = self.applet.Plugins.GetClasses()
		loaded = self.applet.Plugins.GetLoaded()
		for name, cls in classes.iteritems():
			if cls.__unloadable__:
				func = self.list.prepend
			else:
				func = self.list.append
			func(active=(name in loaded), icon=cls.__icon__, activatable=(cls.__unloadable__), name=name)
			
	def plugin_state_changed(self, plugins, name, loaded):
		row = self.list.get_conditional(name=name)
		self.list.set(row[0], active=loaded)
			
		
	def on_toggled(self, cellrenderer, path):
		name = self.list.get(path, "name")["name"]
		
		deps = self.applet.Plugins.GetDependencies()[name]
		loaded = self.applet.Plugins.GetLoaded()
		to_unload = []
		for dep in deps:
			if dep in loaded:
				to_unload.append(dep)
				
		if to_unload != []:
			dialog = gtk.MessageDialog(self, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO)
			dialog.props.secondary_use_markup = True
			dialog.props.icon_name = "blueman"
			dialog.props.text = _("Dependency issue")
			dialog.props.secondary_text = _("Plugin <b>\"%(0)s\"</b> depends on <b>%(1)s</b>. Unloading <b>%(1)s</b> will also unload <b>\"%(0)s\"</b>.\nProceed?") % {"0": ", ".join(to_unload), "1": name}
			
			resp = dialog.run()
			dialog.destroy()
		
		loaded = name in self.applet.Plugins.GetLoaded()
		cls = self.applet.Plugins.SetConfig(name, not loaded)
		
		
		
		
		
