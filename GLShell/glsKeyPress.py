import wx

################################################################

class glsKeyPress():
    shift_key_map = { ',':'<', '.':'>', '/':'?', ';':':', "'":'"', '[' :'{', ']':'}',
                      '1':'!', '2':'@', '3':'#', '4':'$', '5':'%', '6' :'^', '7':'&',
                      '8':'*', '9':'(', '0':')', '-':'_', '=':'+', '\\':'|', '`':'~',
                      '<':'<', '(':'(', ')':')' }

    special_key_map = { wx.WXK_UP:"\x1b[A",   wx.WXK_DOWN:"\x1b[B", wx.WXK_RIGHT:"\x1b[C",
                        wx.WXK_LEFT:"\x1b[D", wx.WXK_ESCAPE:"\x1b", wx.WXK_INSERT:"\x1b[2~",
                        wx.WXK_BACK:"\x7f",   wx.WXK_DELETE:"\x1b[3~", wx.WXK_RETURN:"\x0a" }

    special_alt_key_map = { wx.WXK_UP:"\x1b[1;3A",    wx.WXK_DOWN:"\x1b[1;3B",
                            wx.WXK_RIGHT:"\x1b[1;3C", wx.WXK_LEFT:"\x1b[1;3D" }
    def __init__(self, keys_down):
        self.keys_down = keys_down
        return
    def KeyCodeToSequence(self, key):
        seq = None
        if wx.WXK_ALT in self.keys_down:
            if key in self.special_alt_key_map:
                return self.special_alt_key_map[key]
        if key in self.special_key_map:
            return self.special_key_map[key]
        if key < 256:
            ckey = chr(key)
            if wx.WXK_ALT in self.keys_down:
                seq = "\x1b"
                if wx.WXK_SHIFT in self.keys_down:
                    if ckey in self.shift_key_map:
                       return seq + self.shift_key_map[ckey]
                    return seq + ckey
                return seq + ckey.lower()
            if wx.WXK_CONTROL in self.keys_down:
                if key == wx.WXK_SPACE:
                    return '\x00'
                if wx.WXK_SHIFT in self.keys_down:
                    if ckey >= 'A' and ckey <= 'Z':
                        print('sending',chr(key))
                        return chr(ord(chr(key))-0x40)
                    if ckey == '-':
                        return '\x1f'
                    if ckey == ',' or ckey == '.':
                        return 
                else:
                    if ckey >= 'A' and ckey <= 'Z':
                        return chr(ord(chr(key).lower())-0x60)
            else:
                if wx.WXK_SHIFT in self.keys_down:
                    if ckey in self.shift_key_map:
                        return self.shift_key_map[ckey]
                    else:
                        return ckey
                else:
                    return ckey.lower()
        return seq

################################################################
