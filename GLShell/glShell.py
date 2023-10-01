#!/usr/bin/env python3
#
# GLShell - OpenGL-Enhanced Integrated Development Environment
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
import platform
if 'WAYLAND_DISPLAY' in os.environ and 'PYOPENGL_PLATFORM' not in os.environ:
    os.environ['PYOPENGL_PLATFORM'] = 'egl'
if "Ubuntu" in platform.version():
    os.environ['PYOPENGL_PLATFORM'] = 'egl'
import sys
import wx

from glsTermsPanel import glsTermsPanel
from glsStatusBar import glsStatusBar
from glsDataPanel import glsDataPanel
from glsDirTree import glsDirTree
from glsIcons import glsIcons
import glsSettings
import glsHelp

VERSION = "0.0.8"

################################################################

class glShell(wx.Frame):
    ID_OPEN_DIR  = 1000
    ID_OPEN_FILE = 1001
    ID_LICENSE   = 1002
    ID_ABOUT     = 1003
    ID_SETTINGS  = 1004
    ID_EXIT      = 1005
    def __init__(self, app, settings):
        self.settings = settings
        self.settings.AddWatcher(self.OnChangeSettings)
        self.app = app
        wx.Frame.__init__(self, None, wx.ID_ANY, "GLShell - "+VERSION,
                          size = (1366, 768))
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.OnSplitChanging)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnSplitChanged)
        self.icons = glsIcons()
        self.icon = wx.Icon()
        self.icon.CopyFromBitmap(self.icons.Get('chart_organisation'))
        self.SetIcon(self.icon)
        self.InitUI()
        self.Bind(wx.EVT_TIMER, self.OnStart)
        self.start = wx.Timer(self)
        self.start.StartOnce()
        return
    def OnStart(self, event):
        del self.start
        path = sys.argv[1] if len(sys.argv) == 2 else "."
        self.data_panel.AddDirTree(glsDirTree(path, settings))
        return
    def OnChangeSettings(self, settings):
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
        item.SetBitmap(self.icons.Get('monitor_add'))
        menu_file.Append(item)
        item = wx.MenuItem(menu_file, self.ID_OPEN_DIR, text="Open Directory")
        item.SetBitmap(self.icons.Get('chart_organisation_add'))
        menu_file.Append(item)
        item = wx.MenuItem(menu_file, self.ID_EXIT, text="Quit")
        item.SetBitmap(self.icons.Get('cross'))
        menu_file.Append(item)
        menubar.Append(menu_file, 'File')
        # Edit menu.
        menu_edit = wx.Menu()
        item = wx.MenuItem(menu_edit, self.ID_SETTINGS, text="Settings")
        item.SetBitmap(self.icons.Get('cog'))
        menu_edit.Append(item)
        menubar.Append(menu_edit, 'Edit')
        # Help menu.
        menu_help = wx.Menu()
        item = wx.MenuItem(menu_help, self.ID_ABOUT, text="About")
        item.SetBitmap(self.icons.Get('information'))
        menu_help.Append(item)
        item = wx.MenuItem(menu_help, self.ID_LICENSE, text="License")
        item.SetBitmap(self.icons.Get('script_key'))
        menu_help.Append(item)
        menubar.Append(menu_help, '&Help')
        # Connect menus to menu bar.
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
            self.Destroy()
            return
        if menu_id == self.ID_OPEN_FILE:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            with wx.FileDialog(self, style=style) as file_dialog:
                if file_dialog.ShowModal() != wx.ID_OK:
                    return
                self.terms_panel.EditorStart(file_dialog.GetPath())
            return
        if menu_id == self.ID_OPEN_DIR:
            with wx.DirDialog(self, defaultPath=os.getcwd(),
                              style=wx.DD_DIR_MUST_EXIST) as dir_dialog:
                if dir_dialog.ShowModal() != wx.ID_OK:
                    return
                self.AddDirTree(glsDirTree(dir_dialog.GetPath(), self.settings))
            return
        if menu_id == self.ID_SETTINGS:
            if self.settings_frame is None:
                self.settings_frame = glsSettings.SettingsFrame(self, self.settings)
                self.settings_frame.Show()
                self.settings_frame.Raise()
            else:
                self.settings_frame.Raise()
        elif menu_id == self.ID_ABOUT:
            if self.about_frame is None:
                self.about_frame = glsHelp.glsAboutFrame(self)
            else:
                self.about_frame.Raise()
        elif menu_id == self.ID_LICENSE:
            if self.license_frame is None:
                self.license_frame = glsHelp.glsLicenseFrame(self)
            else:
                self.license_frame.Raise()
        return
    def InitStatusBar(self):
        self.statusbar = glsStatusBar(self)
        self.SetStatusBar(self.statusbar)
        return
    def InitUI(self):
        # Setup menu bar / status bar.
        self.InitMenuBar()
        self.InitStatusBar()
        # Main box.
        box_main = wx.BoxSizer(wx.VERTICAL)
        # DataPanel and TermsPanel side-by-side.
        self.min_term_size = (320, 92)
        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(self.min_term_size[0])
        self.splitter.SetMinSize( (self.min_term_size[0]*2+100, self.min_term_size[1]*2+150) )
        # Terminals.
        self.terms_panel = glsTermsPanel(self.splitter, self.settings, self.min_term_size,
                                         self.OnChildLayout, self.OnSearchFiles,
                                         self.OnSearchContents)
        # Data panel.
        self.data_panel = glsDataPanel(self.splitter, self.settings, self.terms_panel)
        # Finalize UI layout.
        box_main.Add(self.splitter, 1, wx.TOP | wx.BOTTOM | wx.EXPAND, 0)
        self.splitter.SplitVertically(self.data_panel, self.terms_panel)
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnChildLayout(self, tpanel_sz):
        pad = 50
        sash_sz = self.splitter.GetSashSize()
        dpanel_sz = (self.min_term_size[0], -1)
        orig_sz = tuple(self.Size)
        self.tpanel_size = tpanel_sz
        self.splitter.SetMinSize( (dpanel_sz[0] + sash_sz + tpanel_sz[0] + pad,
                                   tpanel_sz[1] + pad) )
        self.splitter.Layout()
        self.SetMinSize((50,50))
        self.Layout()
        self.Fit()
        self.SetMinSize(self.Size)
        new_sz = (max(self.Size[0], orig_sz[0]), max(self.Size[1], orig_sz[1]))
        self.SetSize(-1, -1, *new_sz)
        return
    def OnSplitChanging(self, event):
        graph_size = self.min_term_size[0]
        sash_pos = event.GetSashPosition()
        sash_max = self.splitter.Size[0] - self.tpanel_size[0]
        if sash_pos < graph_size:
            event.SetSashPosition(graph_size)
        if sash_pos > sash_max:
            event.SetSashPosition(sash_max)
        return
    def OnSplitChanged(self, event):
        self.OnSplitChanging(event)
        return
    def AddDirTree(self, dirtree):
        self.data_panel.AddDirTree(dirtree)
        return
    def OnOpenDir(self, path):
        if path == "":
            return
        self.AddDirTree(glsDirTree(path, self.settings))
        return
    def OnSearchFiles(self, text):
        self.data_panel.SearchFiles(text)
        return
    def OnSearchContents(self, text):
        self.data_panel.SearchContents(text)
        return
    def OnClose(self, event=None):
        if self.settings_frame is not None:
            self.settings_frame.OnClose()
        if self.about_frame is not None:
            self.about_frame.OnClose()
        if self.license_frame is not None:
            self.license_frame.OnClose()
        self.data_panel.OnClose()
        self.settings.RemoveWatcher(self.OnChangeSettings)
        if event is not None:
            event.Skip()
        return
    def OnDestroy(self, event):
        self.settings.RemoveWatcher(self.OnChangeSettings)
        return

################################################################

if __name__ == '__main__':
    settings = glsSettings.glsSettings()
    settings.Load()
    app = wx.App(0);
    gl_shell = glShell(app, settings)
    app.SetTopWindow(gl_shell)
    app.MainLoop()

################################################################
