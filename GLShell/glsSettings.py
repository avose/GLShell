import os
import json

################################################################

class glsSettingsManager():
    __watchers = None
    __settings = None
    __defaults = { "path": "~/.glshell",
                   "log_level": 100,
                   "shell_path": "/bin/bash",
                   "shell_args": "",
                   "term_type": "linux",
                   "term_color": True,
                   "term_fgcolor": (192,192,192),
                   "term_bgcolor": (0,0,0),
                   "term_wchars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ"\
                                  "abcdefghijklmnopqrstuvwxyz"\
                                  "-z0123456789,./?%&#:_=+@~",
                   "term_font": "Monospace",
                   "term_font_size": 11,
                   "graph_3D": True,
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
                for key in glsSettingsManager.__settings:
                    glsSettingsManager.__settings[key] = d[key] if key in d else self.Get(key)
        except:
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
        except:
            pass
        return
    def Get(self, key):
        if key in glsSettingsManager.__settings:
            return glsSettingsManager.__settings[key]
        return None
    def Set(self, key, value):
        glsSettingsManager.__settings[key] = value
        self.OnChange()
        return value
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
