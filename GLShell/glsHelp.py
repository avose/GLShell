import wx

class glsAboutFrame(wx.Frame):
    def __init__(self, parent, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER):
        wx.Frame.__init__(self, parent, title="About GLShell", style=style)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        box_main = wx.BoxSizer(wx.VERTICAL)
        box_top = wx.BoxSizer(wx.VERTICAL)
        # Panel to hold text at the top of the about frame.
        self.panel_top = wx.Panel(self )
        box_text = wx.BoxSizer(wx.VERTICAL)
        self.st_title = wx.StaticText(self.panel_top, wx.ID_ANY, "About GLShell:")
        self.st_title.SetFont(wx.Font(wx.FontInfo(11).FaceName("Monospace").Bold()))
        box_text.Add(self.st_title, 0, wx.ALL, 20)
        self.description = 'GL-Shell was first created in the summer of 2023 by Aaron Vose to\n'\
                           'fill a gap in the integrated development environment (IDE) space.\n'\
                           'Existing IDEs such as Visual Studio Code only support a subset of\n'\
                           'commonly used Emacs commands, and the only way to ensure complete\n'\
                           'support is to embed a full Emacs instance inside the IDE. As IDEs\n'\
                           'need support for an embedded terminal emulator anyway, Emacs in a\n'\
                           'terminal is a great choice. Additionally, by letting the terminal\n'\
                           'take center stage, developers will have the ability to use any of\n'\
                           'the available tried-and-true terminal-based editors, from editors\n'\
                           'packed full of features like Emacs and Vim to simple editors like\n'\
                           'Nano and Pico.\n'\
                           '\n'\
                           'The prefix "GL" refers to the use of OpenGL for rendering a novel\n'\
                           'file explorer interface on the left of the IDE. This replaces the\n'\
                           'classic directory tree with a 2D or 3D view of the file structure\n'\
                           'and other properties of your project drawn as a graph laid out by\n'\
                           'a force-directed placement algorithm which simulates anti-gravity\n'\
                           'and spring physics to provide a clean and intuitive presentation.\n'
        self.st_description = wx.StaticText(self.panel_top, wx.ID_ANY, self.description,
                                            size=(585,340))
        self.st_description.SetFont(wx.Font(wx.FontInfo(11).FaceName("Monospace")))
        box_text.Add(self.st_description, 0, wx.LEFT | wx.RIGHT, 20)
        self.panel_top.SetSizerAndFit(box_text)
        box_top.Add(self.panel_top, 0, wx.EXPAND)
        box_main.Add(box_top, 1, wx.EXPAND)
        # OK button to close.
        box_bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_ok = wx.Button(self, wx.ID_ANY, "Ok")
        self.btn_ok.Bind(wx.EVT_BUTTON, self.OnOk)
        box_bottom.Add(self.btn_ok, 0, wx.ALL, 5)
        box_main.Add(box_bottom, 0, wx.ALIGN_RIGHT)
        # Set main box as frame sizer.
        self.SetSizerAndFit(box_main)
        self.Show(True)
        return
    def OnOk(self, event):
        self.OnClose(event)
        return
    def OnClose(self, event):
        self.Parent.about_frame = None
        self.Destroy()
        return
