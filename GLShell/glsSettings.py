import os
import json

################################################################

class glsSettingsManager():
    __watchers = None
    __settings = None
    __defaults = { "path": "~/.glshell",
                   "log_level": 1,
                   "shell_path": "/bin/bash",
                   "shell_args": "",
                   "term_type": "xterm-256color",
                   "term_scroll_output": True,
                   "term_scroll_keypress": True,
                   "term_color": True,
                   "term_fgcolor": (192,192,192),
                   "term_bgcolor": (0,0,0),
                   "term_wchars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"\
                                  "abcdefghijklmnopqrstuvwxyz"\
                                  "-z0123456789,./?%&#:_=+@~",
                   "term_font": "Monospace",
                   "term_font_size": 11,
                   "graph_3D": True,
                   "graph_ignore": (".git", ".svn"),
                   "graph_font": "Monospace",
                   "graph_font_size": 10,
                   "edit_path": "/usr/bin/emacs",
                   "edit_args": "-nw",
                   "edit_open": "\x18\x06{FILE}\x0a",
                   "edit_line": "\x1b\x78goto-line\x0a{LINE}\x0a" }
    def __init__(self):
        if glsSettingsManager.__settings is None:
            glsSettingsManager.__settings = dict(glsSettingsManager.__defaults)
        if glsSettingsManager.__watchers is None:
            glsSettingsManager.__watchers = []
        return
    def Reset(self):
        glsSettingsManager.__settings = dict(glsSettingsManager.__defaults)
        self.OnChange()
        return
    def Load(self, path=None):
        if path is not None:
            self.Set('path', path)
        conf_path = os.path.abspath(os.path.expanduser(self.Get('path')))
        try:
            with open(conf_path,"r") as conf:
                d = json.load(conf)
                settings = glsSettingsManager.__settings
                for key in settings:
                    settings[key] = d.get(key, self.Get(key))
                    if type(settings[key]) == type([]):
                        settings[key] = tuple(settings[key])
        except FileNotFoundError:
            self.Save()
            pass
        self.OnChange()
        return
    def Save(self,path=None):
        if path is not None:
            self.Set('path', path)
        conf_path = os.path.abspath(os.path.expanduser(self.Get('path')))
        try:
            with open(conf_path,"w") as conf:
                json.dump(glsSettingsManager.__settings, conf, indent=2)
        except FileNotFoundError:
            pass
        return
    def Get(self, key):
        return glsSettingsManager.__settings.get(key, None)
    def Set(self, key, value, callback=True):
        if key not in glsSettingsManager.__settings:
            raise Exception("glsSettingsManager(): Invalid Setting '%s'."%
                            (str(key)))
        if type(value) != type(glsSettingsManager.__settings[key]):
            raise Exception("glsSettingsManager(): Type Missmatch ['%s']: '%s' != '%s'."%
                            (str(key), type(value), type(glsSettingsManager.__settings[key])))
        if type(value) == type([]):
            value = tuple(value)
        glsSettingsManager.__settings[key] = value
        if callback:
            self.OnChange()
        return value
    def SetList(self, settings_list):
        for key, value in settings_list:
            self.Set(key, value, callback=False)
        self.OnChange()
        return
    def OnChange(self):
        # Call this method if settings have changed.
        for watcher in glsSettingsManager.__watchers:
            watcher()
        return
    def AddWatcher(self, callback):
        glsSettingsManager.__watchers.append(callback)
        return
    def RemoveWatcher(self, callback):
        if callback in glsSettingsManager.__watchers:
            glsSettingsManager.__watchers.remove(callback)
        return

################################################################

glsSettings = glsSettingsManager()

################################################################
