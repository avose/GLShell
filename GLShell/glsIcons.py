import wx
import os

################################################################

class glsIcons():
    __icons = None
    def __init__(self):
        if glsIcons.__icons is not None:
            return
        glsIcons.__icons = {}
        img_dir = os.path.dirname(os.path.abspath(__file__))
        img_dir = os.path.join(img_dir,"icons")
        for fname in os.listdir(img_dir):
            img_name, ext = os.path.splitext(fname)
            if ext != ".png":
                continue
            img_path = os.path.join(img_dir, fname)
            bmp = wx.Bitmap(wx.Image(img_path, wx.BITMAP_TYPE_ANY))
            glsIcons.__icons[img_name] = bmp
        return
    def Get(self, name):
        if name in glsIcons.__icons:
            return glsIcons.__icons[name]
        return None

################################################################
