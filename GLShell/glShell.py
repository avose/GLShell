#!/usr/bin/env python3
#
# GLShell - Terminal Emulator
# Copyright (C) 2023 Aaron D Vose
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# 02111-1307  USA
#
# Aaron D Vose
# avose@aaronvose.net
#
# See TermEmulator.py:
# TermEmulator - Emulator for VT100 terminal programs
# Copyright (C) 2008 Siva Chandran P
#
# Siva Chandran P
# siva.chandran.p@gmail.com

from __future__ import print_function

import os
import sys
import wx

from glsSettingsDialog import glsSettingsDialog
from glsTermsPanel import glsTermsPanel
from glsStatusBar import glsStatusBar
from glsSettings import glsSettings
from glsVersion import glsVersion
from glsEvents import glsEvents
from glsIcons import glsIcons
from glsHelp import glsLicenseFrame
from glsHelp import glsAboutFrame
from glsApp import glsApp

################################################################

class glShell(wx.Frame):
    ID_OPEN_FILE = 1000
    ID_LICENSE   = 1001
    ID_ABOUT     = 1002
    ID_SETTINGS  = 1003
    ID_EXIT      = 1004
    def __init__(self, app):
        glsSettings.AddWatcher(self.OnChangeSettings)
        self.app = app
        wx.Frame.__init__(self, None, wx.ID_ANY, "GLShell - "+glsVersion,
                          size = (1024, 768))
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.icon = wx.Icon()
        self.icon.CopyFromBitmap(glsIcons.Get('monitor'))
        self.SetIcon(self.icon)
        self.InitUI()
        return
    def OnChangeSettings(self):
        return
    def OnCharHook(self, event):
        event.DoAllowNextEvent()
        event.Skip()
        return
    def InitMenuBar(self):
        menubar = wx.MenuBar()
        # File menu.
        menu_file = wx.Menu()
        item = wx.MenuItem(menu_file, self.ID_OPEN_FILE, text="Open File")
        item.SetBitmap(glsIcons.Get('monitor_add'))
        menu_file.Append(item)
        item = wx.MenuItem(menu_file, self.ID_EXIT, text="Quit")
        item.SetBitmap(glsIcons.Get('cross'))
        menu_file.Append(item)
        menubar.Append(menu_file, 'File')
        # Edit menu.
        menu_edit = wx.Menu()
        item = wx.MenuItem(menu_edit, self.ID_SETTINGS, text="Settings")
        item.SetBitmap(glsIcons.Get('cog'))
        menu_edit.Append(item)
        menubar.Append(menu_edit, 'Edit')
        # Help menu.
        menu_help = wx.Menu()
        item = wx.MenuItem(menu_help, self.ID_ABOUT, text="About")
        item.SetBitmap(glsIcons.Get('information'))
        menu_help.Append(item)
        item = wx.MenuItem(menu_help, self.ID_LICENSE, text="License")
        item.SetBitmap(glsIcons.Get('script_key'))
        menu_help.Append(item)
        menubar.Append(menu_help, '&Help')
        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.MenuHandler)
        self.settings_frame = None
        self.about_frame = None
        self.license_frame = None
        return
    def MenuHandler(self, event):
        menu_id = event.GetId()
        if menu_id == self.ID_EXIT:
            self.OnClose()
            return
        if menu_id == self.ID_OPEN_FILE:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            with wx.FileDialog(self, style=style) as file_dialog:
                if file_dialog.ShowModal() != wx.ID_OK:
                    return
                self.terms_panel.EditorStart(file_dialog.GetPath())
            return
        if menu_id == self.ID_SETTINGS:
            if self.settings_frame is None:
                self.settings_frame = glsSettingsDialog(self)
                self.settings_frame.Show()
                self.settings_frame.Raise()
            else:
                self.settings_frame.Raise()
            return
        if menu_id == self.ID_ABOUT:
            if self.about_frame is None:
                self.about_frame = glsAboutFrame(self)
            else:
                self.about_frame.Raise()
            return
        if menu_id == self.ID_LICENSE:
            if self.license_frame is None:
                self.license_frame = glsLicenseFrame(self)
            else:
                self.license_frame.Raise()
            return
        return
    def InitStatusBar(self):
        self.statusbar = glsStatusBar(self)
        self.SetStatusBar(self.statusbar)
        return
    def InitUI(self):
        self.InitMenuBar()
        self.InitStatusBar()
        box_main = wx.BoxSizer(wx.VERTICAL)
        self.min_term_size = (320, 92)
        self.terms_panel = glsTermsPanel(self, self.min_term_size,
                                         self.OnChildLayout)
        box_main.Add(self.terms_panel, 1, wx.EXPAND)
        self.SetSizer(box_main)
        self.Show(True)
        return
    def OnChildLayout(self, tpanel_sz):
        pad = 50
        min_sz = (tpanel_sz[0] + pad, tpanel_sz[1] + pad)
        orig_sz = tuple(self.Size)
        self.SetMinSize(min_sz)
        self.Layout()
        new_sz = (max(self.Size[0], orig_sz[0]), max(self.Size[1], orig_sz[1]))
        self.SetSize(-1, -1, *new_sz)
        return
    def OnClose(self, event=None):
        msg = "Are you sure you want to exit?\n\nYou will lose any unsaved work."
        with wx.MessageDialog(self, msg, caption="Exit GLShell?",
                              style=wx.OK|wx.CANCEL) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                if event is not None:
                    event.StopPropagation()
                return
        if self.settings_frame is not None:
            self.settings_frame.OnClose()
        if self.about_frame is not None:
            self.about_frame.OnClose()
        if self.license_frame is not None:
            self.license_frame.OnClose()
        glsSettings.RemoveWatcher(self.OnChangeSettings)
        self.Destroy()
        return
    def OnDestroy(self, event):
        glsSettings.RemoveWatcher(self.OnChangeSettings)
        return

################################################################

if __name__ == '__main__':
    glsSettings.Load()
    app = glsApp.get()
    glshell = glShell(app)
    app.SetTopWindow(glshell)
    app.MainLoop()

################################################################
