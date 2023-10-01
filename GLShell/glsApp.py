import wx

################################################################

class glsAppManager():
    __wxapp = None
    def __init__(self):
        if glsAppManager.__wxapp is None:
            glsAppManager.__wxapp = wx.App(0)
        return
    def get(self):
        return glsAppManager.__wxapp

################################################################

glsApp = glsAppManager()

################################################################
