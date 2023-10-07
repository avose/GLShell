# TermEmulator - Emulator for VT100 terminal programs
# Copyright (C) 2008 Siva Chandran P
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
# Siva Chandran P
# siva.chandran.p@gmail.com
#
# Source code modified beginning in August 2023:
# Aaron D. Vose.
# avose@aaronvose.net

"""
Emulator for VT100+ terminal programs.

This module provides terminal emulation for VT100+ terminal programs. It handles
V100 special characters and most important escape sequences. It also handles
graphics rendition which specifies text style (i.e. bold, italics), foreground color
and background color. New sequences from Xterm and the Linux terminal are added.
"""

from __future__ import print_function

import os
import sys
import pty
import select
import traceback
from array import *

from glsVersion import glsVersion
from glsLog import glsLog

class V102Terminal:
    __ASCII_NUL = 0         # Null
    __ASCII_BEL = 7         # Bell
    __ASCII_BS = 8          # Backspace
    __ASCII_HT = 9          # Horizontal Tab
    __ASCII_LF = 10         # Line Feed
    __ASCII_VT = 11         # Vertical Tab
    __ASCII_FF = 12         # Form Feed
    __ASCII_CR = 13         # Carriage Return
    __ASCII_SO = 14         # Shift out to G1 character set
    __ASCII_SI = 15         # Shift in to G0 character set
    __ASCII_XON = 17        # Resume Transmission
    __ASCII_XOFF = 19       # Stop Transmission or Ignore Characters
    __ASCII_ESC = 27        # Escape
    __ASCII_SPACE = 32      # Space
    __ASCII_CSI = 155       # Control Sequence Introducer #!!avose: was 153

    __ESCSEQ_ICH_SL = '@'   # [n] [ ] @: Without space: insert n blank characters,
                            # default 1. With space: Shift left n columns(s),
                            # default 1.

    __ESCSEQ_CUU = 'A'      # n A: Moves the cursor up n(default 1) times.
    __ESCSEQ_CUD = 'B'      # n B: Moves the cursor down n(default 1) times.
    __ESCSEQ_CUF = 'C'      # n C: Moves the cursor forward n(default 1) times.
    __ESCSEQ_CUB = 'D'      # n D: Moves the cursor backward n(default 1) times.

    __ESCSEQ_CHA = 'G'      # n G: Cursor horizontal absolute position. 'n' denotes
                            # the column no(1 based index). Should retain the line
                            # position.

    __ESCSEQ_CUP = 'H'      # n ; m H: Moves the cursor to row n, column m.
                            # The values are 1-based, and default to 1 (top left
                            # corner).

    __ESCSEQ_ED = 'J'       # n J: Clears part of the screen. If n is zero
                            # (or missing), clear from cursor to end of screen.
                            # If n is one, clear from cursor to beginning of the
                            # screen. If n is two, clear entire screen.

    __ESCSEQ_EL = 'K'       # n K: Erases part of the line. If n is zero
                            # (or missing), clear from cursor to the end of the
                            # line. If n is one, clear from cursor to beginning of
                            # the line. If n is two, clear entire line. Cursor
                            # position does not change.

    __ESCSEQ_IL = 'L'       # [n] L: Insert n blank lines, default 1.

    __ESCSEQ_DL = 'M'       # [n] M: Delete n lines, default 1.

    __ESCSEQ_DCH = 'P'      # [n] P: Delete n characters, default 1.

    __ESCSEQ_VPA = 'd'      # n d: Cursor vertical absolute position. 'n' denotes
                            # the line no(1 based index). Should retain the column
                            # position.

    __ESCSEQ_SGR = 'm'      # n [;k] m: Sets SGR (Select Graphic Rendition)
                            # parameters. After CSI can be zero or more parameters
                            # separated with ;. With no parameters, CSI m is treated
                            # as CSI 0 m (reset / normal), which is typical of most
                            # of the ANSI codes.

    __ESCSEQ_DSR = 'n'      # n: Device Status Report. n == 5 => Request Operating
                            # Status. n == 6 => Request Cursor Position.

    __ESCSEQ_SM = 'h'       # [?] n h: Sets a mode; there are 14 modes defined for a
                            # vt102. While not all modes are supported, some extra
                            # modes commonly used with other terminal types may be
                            # supported.

    __ESCSEQ_RM = 'l'       # [?] n l: Clears a mode; there are 14 modes defined for a
                            # vt102. While not all modes are supported, some extra
                            # modes commonly used with other terminal types may be
                            # supported.

    __ESCSEQ_DECSCUSR = 'q' # n ' ' q: Select cursor style.

    __ESCSEQ_DECSTBM = 'r'  # Multiple escape sequences end in 'r'. One of the more
                            # important ones is the scrolling region: "n ; m r" which
                            # limits effect of scrolling to specified range of lines.

    __ESCSEQ_CSZ = 'c'      # Multiple escape sequences end in 'c'. One of the more
                            # important ones is setting the cursor size / style:
                            # "? n c", where n is the style.

    __ESCSEQ_TWS = 't'      # Multiple escape sequences which interact with the
                            # terminal window, from Xterm. Includes window title.


    __ESC_IND = 'D'         # Non-CSI: Index (linefeed).
    __ESC_NEL = 'E'         # Non-CSI: Next line (CR+LF).
    __ESC_RI = 'M'          # Non-CSI: Reverse index (reverse linefeed).
    __ESC_DECSC = '7'       # Non-CSI: Save cursor state.
    __ESC_DECRC = '8'       # Non-CSI: Restore cursor.
    __ESC_DECPNM = '>'      # Non-CSI: keyPad Numeric Mode.
    __ESC_DECPAM = '='      # Non-CSI: keyPad Application Mode.

    # A large number of extended escape sequences have the form:
    # '\x1b' <params> [ '\x07', '\x1b\\' ]
    #
    # These are almost all new sequences which were added by Xterm and
    # modern terminals.  These sequences are better distinguished by
    # their starting characters rather than by their ending character.

    __EX_ICON_TITLE = ']0;' # Set icon name and terminal title.

    # vt102 modes.
    MODE_KAM     = '2'      # Keyboard action
    MODE_IRM     = '4'      # Insert-replace
    MODE_SRM     = '12'     # Send-receive
    MODE_LMN     = '20'     # Linefeed / new line
    MODE_DECCKM  = '?1'     # Cursor key
    MODE_DECANM  = '?2'     # ANSI / VT52
    MODE_DECCOLM = '?3'     # Column
    MODE_DECSCLM = '?4'     # Scrolling
    MODE_DECSCNM = '?5'     # Screen
    MODE_DECOM   = '?6'     # Origin
    MODE_DECAWM  = '?7'     # Auto wrap
    MODE_DECARM  = '?8'     # Auto repeat
    MODE_DECPFF  = '?18'    # Print form feed
    MODE_DECPEX  = '?19'    # Print extent
    MODE_DECPNM = 'DECPNM'  # keyPad Numeric Mode
    MODE_DECPAM = 'DECPAM'  # keyPad Application Mode
    # Xterm and newer modes.
    MODE_BLINK   = '?12'    # Cursor blinking
    MODE_DECTCEM = '?25'    # Show cursor
    MODE_RFC     = '?1004'  # Report focus change
    MODE_ALTBUF  = '?47'    # Aternative screen buffer
    MODE_ALTB_SCO= '?1047'  # ALTBUF with save and clear on out
    MODE_ALTB_CSR= '?1048'  # DECSC on ALTBUF in and DECRC on ALTBUF out
    MODE_ALTB_SCI= '?1049'  # ALTBUF with save and clear on in
    MODE_BRCKPST = '?2004'  # Bracketed paste mode

    CURSOR_STYLE_DEFAULT = 0
    CURSOR_STYLE_INVISIBLE = 1
    CURSOR_STYLE_UNDERLINE = 2
    CURSOR_STYLE_BLOCK = 8
    CURSOR_STYLE_BAR = 32
    
    RENDITION_STYLE_BOLD = 1
    RENDITION_STYLE_DIM = 2
    RENDITION_STYLE_ITALIC = 4
    RENDITION_STYLE_UNDERLINE = 8
    RENDITION_STYLE_SLOW_BLINK = 16
    RENDITION_STYLE_FAST_BLINK = 32
    RENDITION_STYLE_INVERSE = 64
    RENDITION_STYLE_HIDDEN = 128

    CALLBACK_SCROLL_UP_SCREEN = 0
    CALLBACK_UPDATE_LINES = 1
    CALLBACK_UPDATE_CURSOR_POS = 2
    CALLBACK_UPDATE_WINDOW_TITLE = 3
    CALLBACK_UPDATE_MODE = 4
    CALLBACK_UPDATE_CURSOR = 5
    CALLBACK_SEND_DATA = 6

    def __init__(self, rows, cols):
        """
        Initializes the terminal with specified rows and columns. User can
        resize the terminal any time using Resize method. By default the screen
        is cleared (filled with blank spaces) and cursor positioned in the first
        row and first column with the entire scrren in the scroll region.
        """
        self.cols = cols
        self.rows = rows
        self.ignoreChars = False
        self.scrollRegion = (0, self.rows-1)

        # cursor state
        self.cursorStyle = self.CURSOR_STYLE_DEFAULT
        self.curX = 0
        self.curY = 0
        self.savedCursor = [ (self.curY, self.curX, self.cursorStyle, 0),
                             (self.curY, self.curX, self.cursorStyle, 0) ]

        # special character handlers
        self.charHandlers = { self.__ASCII_NUL: self.__OnCharIgnore,
                              self.__ASCII_BEL: self.__OnCharIgnore,
                              self.__ASCII_BS:  self.__OnCharBS,
                              self.__ASCII_HT:  self.__OnCharHT,
                              self.__ASCII_LF:  self.__OnCharLF,
                              self.__ASCII_VT:  self.__OnCharLF,
                              self.__ASCII_FF:  self.__OnCharLF,
                              self.__ASCII_CR:  self.__OnCharCR,
                              self.__ASCII_XON: self.__OnCharXON,
                              self.__ASCII_XOFF:self.__OnCharXOFF,
                              self.__ASCII_ESC: self.__OnCharESC,
                              self.__ASCII_CSI: self.__OnCharCSI,
                              self.__ASCII_SO:  self.__OnCharSO,
                              self.__ASCII_SI:  self.__OnCharSI, }

        # escape sequence handlers
        self.escSeqHandlers = { self.__ESCSEQ_ICH_SL:  self.__OnEscSeqICH_SL,
                                self.__ESCSEQ_CUU:     self.__OnEscSeqCUU,
                                self.__ESCSEQ_CUD:     self.__OnEscSeqCUD,
                                self.__ESCSEQ_CUF:     self.__OnEscSeqCUF,
                                self.__ESCSEQ_CUB:     self.__OnEscSeqCUB,
                                self.__ESCSEQ_CHA:     self.__OnEscSeqCHA,
                                self.__ESCSEQ_CUP:     self.__OnEscSeqCUP,
                                self.__ESCSEQ_ED:      self.__OnEscSeqED,
                                self.__ESCSEQ_EL:      self.__OnEscSeqEL,
                                self.__ESCSEQ_IL:      self.__OnEscSeqIL,
                                self.__ESCSEQ_DL:      self.__OnEscSeqDL,
                                self.__ESCSEQ_DCH:     self.__OnEscSeqDCH,
                                self.__ESCSEQ_VPA:     self.__OnEscSeqVPA,
                                self.__ESCSEQ_SGR:     self.__OnEscSeqSGR,
                                self.__ESCSEQ_DSR:     self.__OnEscSeqDSR,
                                self.__ESCSEQ_SM:      self.__OnEscSeqSM,
                                self.__ESCSEQ_RM:      self.__OnEscSeqRM,
                                self.__ESCSEQ_DECSCUSR:self.__OnEscSeqDECSCUSR,
                                self.__ESCSEQ_DECSTBM: self.__OnEscSeqDECSTBM,
                                self.__ESCSEQ_CSZ:     self.__OnEscSeqCSZ,
                                self.__ESCSEQ_TWS:     self.__OnEscSeqTWS, }

        # ESC- but not CSI-sequences
        self.escHandlers = { self.__ESC_IND:   self.__OnEscIND,
                             self.__ESC_NEL:   self.__OnEscNEL,
                             self.__ESC_RI:    self.__OnEscRI,
                             self.__ESC_DECSC: self.__OnEscDECSC,
                             self.__ESC_DECRC: self.__OnEscDECRC,
                             self.__ESC_DECPNM:self.__OnEscDECPNM,
                             self.__ESC_DECPAM:self.__OnEscDECPAM, }

        # extended escape sequences
        self.exHandlers = { self.__EX_ICON_TITLE:self.__OnExICON_TITLE }

        # terminal modes
        self.modes = { self.MODE_BLINK:   False,
                       self.MODE_DECTCEM: True,
                       self.MODE_BRCKPST: False,
                       self.MODE_ALTBUF:  False,
                       self.MODE_ALTB_SCO:False,
                       self.MODE_ALTB_CSR:False,
                       self.MODE_ALTB_SCI:False, }

        # mode handlers for mode enter / exit
        self.modeHandlers = { self.MODE_ALTBUF:  self.__OnModeALTBUF,
                              self.MODE_ALTB_SCO:self.__OnModeALTBUF_SCO,
                              self.MODE_ALTB_CSR:self.__OnModeALTBUF_SCR,
                              self.MODE_ALTB_SCI:self.__OnModeALTBUF_SCI, }

        # defines the printable characters, only these characters are printed
        # on the terminal
        self.printableChars = "0123456789"
        self.printableChars += "abcdefghijklmnopqrstuvwxyz"
        self.printableChars += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.printableChars += """!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~ """
        self.printableChars += "\t"

        # terminal screen, its a list of string in which each string always
        # holds self.cols characters. If the screen doesn't contain any
        # character then it'll blank space
        self.screen = []

        # terminal screen rendition, its a list of array of long. The first
        # 8 bits of the long holds the rendition style/attribute(i.e. bold,
        # italics and etc). The next 4 bits specifies the foreground color and
        # next 4 bits for background
        self.scrRendition = []

        # current rendition
        self.curRendition = 0

        # initialize screen and rendition arrays
        for i in range(rows):
            line = array('u')
            rendition = array('L')
            color = array('L')
            for j in range(cols):
                line.append(u' ')
                rendition.append(0)
            self.screen.append(line)
            self.scrRendition.append(rendition)

        # initialize saved screen
        self.savedScreen = []
        self.savedRendition = []
        for scrl,renl in zip(self.screen, self.scrRendition):
            self.savedScreen.append(array('u', scrl))
            self.savedRendition.append(array('L', renl))

        # initializes callbacks
        self.callbacks = { self.CALLBACK_SCROLL_UP_SCREEN: None,
                           self.CALLBACK_UPDATE_LINES: None,
                           self.CALLBACK_UPDATE_CURSOR_POS: None,
                           self.CALLBACK_UPDATE_WINDOW_TITLE: None,
                           self.CALLBACK_UPDATE_MODE: None,
                           self.CALLBACK_UPDATE_CURSOR: None,
                           self.CALLBACK_SEND_DATA: None, }

        # unparsed part of last input
        self.unparsedInput = None
        return
    def GetRawScreen(self):
        """
        Returns the screen as a list of strings. The list will have rows no. of
        strings and each string will have columns no. of characters. Blank space
        used represents no character.
        """
        return self.screen
    def GetRawScreenRendition(self):
        """
        Returns the screen as a list of array of long. The list will have rows
        no. of array and each array will have columns no. of longs. The first
        8 bits of long represents rendition style like bold, italics and etc.
        The next 4 bits represents foreground color and next 4 bits for
        background color.
        """
        return self.scrRendition
    def GetRows(self):
        """
        Returns no. rows in the terminal
        """
        return self.rows
    def GetCols(self):
        """
        Returns no. cols in the terminal
        """
        return self.cols
    def GetSize(self):
        """
        Returns terminal rows and cols as tuple
        """
        return (self.rows, self.cols)
    def Resize(self, rows, cols):
        """
        Resizes the terminal to specified rows and cols.
        - If the new no. rows is less than existing no. rows then existing rows
          are deleted at top.
        - If the new no. rows is greater than existing no. rows then
          blank rows are added at bottom.
        - If the new no. cols is less than existing no. cols then existing cols
          are deleted at right.
        - If the new no. cols is greater than existing no. cols then new cols
          are added at right.
        """
        new_x = min(max(self.curX, 0), self.cols-1)
        new_y = min(max(self.curY, 0), self.rows-1)
        if new_x != self.curX or new_y != self.curY:
            self.curX = new_x
            self.curY = new_y
            self.__Callback(self.CALLBACK_UPDATE_CURSOR_POS)
        cur_rows = len(self.screen)
        cur_cols = len(self.screen[0])
        if rows < cur_rows:
            # remove rows at top
            for i in range(cur_rows - rows):
                self.screen.pop(0)
                self.scrRendition.pop(0)
        elif rows > cur_rows:
            # add blank rows at bottom
            for i in range(rows - cur_rows):
                line = array('u')
                rendition = array('L')
                for j in range(cur_cols):
                    line.append(u' ')
                    rendition.append(0)
                self.screen.append(line)
                self.scrRendition.append(rendition)
        self.rows = rows
        if cols < cur_cols:
            # remove cols at right
            for i in range(self.rows):
                self.screen[i] = self.screen[i][:cols - cur_cols]
                for j in range(cur_cols - cols):
                    self.scrRendition[i].pop(len(self.scrRendition[i]) - 1)
        elif cols > cur_cols:
            # add cols at right
            for i in range(self.rows):
                for j in range(cols - cur_cols):
                    self.screen[i].append(u' ')
                    self.scrRendition[i].append(0)
        self.cols = cols
        #!!avose: maintain state somehow?
        self.scrollRegion = (0, self.rows-1)
        return
    def GetCursorPos(self):
        """
        Returns cursor position as tuple
        """
        return (self.curY, self.curX)
    def Clear(self):
        """
        Clears the entire terminal screen
        """
        self.ClearRect(0, 0, self.rows - 1, self.cols - 1)
        return
    def ClearRect(self, startRow, startCol, endRow, endCol):
        """
        Clears the terminal screen starting from startRow and startCol to
        endRow and EndCol.
        """
        if startRow < 0:
            startRow = 0
        elif startRow >= self.rows:
            startRow = self.rows - 1
        if startCol < 0:
            startCol = 0
        elif startCol >= self.cols:
            startCol = self.cols - 1
        if endRow < 0:
            endRow = 0
        elif endRow >= self.rows:
            endRow = self.rows - 1
        if endCol < 0:
            endCol = 0
        elif endCol >= self.cols:
            endCol = self.cols - 1
        if startRow > endRow:
            startRow, endRow = endRow, startRow
        if startCol > endCol:
            startCol, endCol = endCol, startCol
        for i in range(startRow, endRow + 1):
            start = 0
            end = self.cols - 1
            if i == startRow:
                start = startCol
            elif i == endRow:
                end = endCol
            for j in range(start, end + 1):
                self.screen[i][j] = ' '
                self.scrRendition[i][j] = 0
        return
    def GetChar(self, row, col):
        """
        Returns the character at the location specified by row and col. The
        row and col should be in the range 0..rows - 1 and 0..cols - 1."
        """
        if row < 0 or row >= self.rows:
            return None
        if col < 0 or col >= self.cols:
            return None
        return self.screen[row][col]
    def GetRendition(self, row, col):
        """
        Returns the screen rendition at the location specified by row and col.
        The returned value is a long, the first 8 bits specifies the rendition
        style and next 4 bits for foreground and another 4 bits for background
        color.
        """
        if row < 0 or row >= self.rows:
            return None
        if col < 0 or col >= self.cols:
            return None
        style = self.scrRendition[row][col] & 0x0000ffff
        fgcolor = (self.scrRendition[row][col] & 0x00ff0000) >> 16
        bgcolor = (self.scrRendition[row][col] & 0xff000000) >> 24
        return (style, fgcolor, bgcolor)
    def GetLine(self, lineno):
        """
        Returns the terminal screen line specified by lineno. The line is
        returned as string, blank space represents empty character. The lineno
        should be in the range 0..rows - 1
        """
        if lineno < 0 or lineno >= self.rows:
            return None
        return self.screen[lineno].tostring()
    def GetLines(self):
        """
        Returns terminal screen lines as a list, same as GetScreen
        """
        lines = []
        for i in range(self.rows):
            lines.append(self.screen[i].tostring())
        return lines
    def GetLinesAsText(self):
        """
        Returns the entire terminal screen as a single big string. Each row
        is seperated by \\n and blank space represents empty character.
        """
        text = ""
        for i in range(self.rows):
            text += self.screen[i].tostring()
            text += '\n'
        text = text.rstrip("\n") # removes leading new lines
        return text
    def SetCallback(self, event, func):
        """
        Sets callback function for the specified event. The event should be
        any one of the following. None can be passed as callback function to
        reset the callback.

        CALLBACK_SCROLL_UP_SCREEN
            Called before scrolling up the terminal screen.

        CALLBACK_UPDATE_LINES
            Called when ever some lines need to be updated. Usually called
            before leaving ProcessInput and before scrolling up the
            terminal screen.

        CALLBACK_UPDATE_CURSOR_POS
            Called to update the cursor position. Usually called before leaving
            ProcessInput.

        CALLBACK_UPDATE_WINDOW_TITLE
            Called when ever a window title escape sequence encountered. The
            terminal window title will be passed as a string.

        CALLBACK_UPDATE_MODE
            Called whenever a terminal mode has changed. A dictionary of modes
            and their settings (True/False) will be passed as an argument.

        CALLBACK_UPDATE_CURSOR
            Called whenever a the cursor has changed. The new style will be
            passed as an argument.

        CALLBACK_SEND_DATA
            Called whenever the terminal emulator needs to send data to the child.
            The data to send will be passed as an argument.
        """
        self.callbacks[event] = func
        return
    def ProcessInput(self, text):
        """
        Processes the given input text. It detects V100 escape sequences and
        handles it. Any partial unparsed escape sequences are stored internally
        and processed along with next input text. Before leaving, the function
        calls the callbacks CALLBACK_UPDATE_LINE and CALLBACK_UPDATE_CURSOR_POS
        to update the changed lines and cursor position respectively.
        """
        if text == None:
            return
        if self.unparsedInput != None:
            text = self.unparsedInput + text
            self.unparsedInput = None
        textlen = len(text)
        index = 0
        while index < textlen:
            ch = text[index]
            ascii = ord(ch)
            if self.ignoreChars:
                index += 1
                continue
            if ascii in self.charHandlers.keys():
                index = self.charHandlers[ascii](text, index)
                continue
            if ch in self.printableChars:
                self.__PushChar(ch)
            else:
                glsLog.debug("TE: Unsupported Character: '%s' (%d)"%
                             (ch, ascii), 1)
            index += 1
        # update the dirty lines
        self.__Callback(self.CALLBACK_UPDATE_LINES)
        # update cursor position
        self.__Callback(self.CALLBACK_UPDATE_CURSOR_POS)
        return
    def ScrollUp(self):
        """
        Scrolls up the terminal screen by one line. The callbacks
        CALLBACK_UPDATE_LINES and CALLBACK_SCROLL_UP_SCREEN are called before
        scrolling the screen.
        """
        if self.scrollRegion[0] == 0 and self.scrollRegion[1] == self.rows-1:
            # update the dirty lines
            self.__Callback(self.CALLBACK_UPDATE_LINES)
            # scrolls up the screen
            if not self.modes[self.MODE_ALTBUF]:
                self.__Callback(self.CALLBACK_SCROLL_UP_SCREEN)
        glsLog.debug("TE: Scroll Up: rg = (%d,%d) term.rows = %d"%
                     (self.scrollRegion[0], self.scrollRegion[1], self.rows), 3)
        line = self.screen.pop(self.scrollRegion[0])
        for i in range(self.cols):
            line[i] = u' '
        self.screen.insert(self.scrollRegion[1], line)
        rendition = self.scrRendition.pop(self.scrollRegion[0])
        for i in range(self.cols):
            rendition[i] = 0
        self.scrRendition.insert(self.scrollRegion[1], rendition)
        return
    def ScrollDown(self):
        line = self.screen.pop(self.scrollRegion[1])
        for i in range(self.cols):
            line[i] = u' '
        self.screen.insert(self.scrollRegion[0], line)
        rendition = self.scrRendition.pop(self.scrollRegion[1])
        for i in range(self.cols):
            rendition[i] = 0
        self.scrRendition.insert(self.scrollRegion[0], rendition)
        glsLog.debug("TE: Scroll Down: rg = (%d,%d) term.rows = %d"%
                     (self.scrollRegion[0], self.scrollRegion[1], self.rows), 3)
        return
    def Dump(self, file=sys.stdout):
        """
        Dumps the entire terminal screen into the given file/stdout
        """
        for i in range(self.rows):
            file.write(self.screen[i].tostring())
            file.write("\n")
        return
    def __Callback(self, callback, *args):
        if callback in self.callbacks:
            self.callbacks[callback](*args)
        return
    def __NewLine(self):
        """
        Moves the cursor to the next line, if the cursor is already at the
        bottom row then scroll up.
        """
        glsLog.debug("TE: Newline: @ (%d,%d) SR=%d,%d rows=%d"%
                     (self.curY, self.curX, self.scrollRegion[0], self.scrollRegion[1],
                      self.rows), 3)
        if self.curY >= self.scrollRegion[0] and self.curY <= self.scrollRegion[1]:
            if self.curY + 1 <= self.scrollRegion[1]:
                self.curY += 1
            else:
                self.ScrollUp()
            return
        if self.curY + 1 < self.rows:
            self.curY += 1
        return
    def __PushChar(self, ch):
        """
        Writes the character (ch) into current cursor position and advances
        cursor position.
        """
        glsLog.debug("TE: Push Char: '%s' @ (%d,%d)"%(ch, self.curY, self.curX), 10)
        if self.curX >= self.cols:
            self.__NewLine()
            self.curX = 0
        self.screen[self.curY][self.curX] = ch
        self.scrRendition[self.curY][self.curX] = self.curRendition
        self.curX += 1
        return
    def __UnhandledEscSeq(self, seq, ex=False):
        printable_seq = ""
        for c in seq:
            if c in self.printableChars:
                printable_seq += c
                if c == "\\":
                    printable_seq += c
            else:
                esc = hex(ord(c)).replace('0x','')
                if len(esc) < 2:
                    esc = '0' + esc
                printable_seq += '\\x' + esc
        glsLog.debug("TE: Unhandled %s Sequence: '%s'"%
                     ('EX ESC' if ex else 'ESC', printable_seq), 1)
        return
    def __ParseEscSeq(self, text, index):
        """
        Parses escape sequence from the input and returns the index after escape
        sequence, the escape sequence character and parameter for the escape
        sequence
        """
        textlen = len(text)
        interChars = None
        while index < textlen:
            ch = text[index]
            ascii = ord(ch)
            if ascii >= 32 and ascii <= 63:
                # intermediate char (32 - 47)
                # parameter chars (48 - 63)
                if interChars == None:
                    interChars = ch
                else:
                    interChars += ch
            elif ascii >= 64 and ascii <= 125:
                # final char
                return (index + 1, chr(ascii), interChars)
            else:
                glsLog.debug("TE: Unexpected character in escape sequence: %s"%ch, 1)
            index += 1
        # the escape sequence is not complete, inform this to caller by giving
        # '?' as final char
        return (index, '?', interChars)
    def __ParseExtendedSeq(self, first, text, index):
        textlen = len(text)
        params = []
        kind = None
        while index < textlen:
            ch = text[index]
            if ch == '\x07':
                # Sequence ended with a bell.
                index += 1
                kind = '' if kind is None else kind
                params = ''.join(params)
                params = None if params == '' else params
                return (index, kind, params)
            if ch == '\x1b':
                if index + 1 < textlen:
                    index += 1
                    if text[index] == '\\':
                        # Sequence is complete.
                        index += 1
                        kind = '' if kind is None else kind
                        params = ''.join(params)
                        params = None if params == '' else params
                        return (index, kind, params)
                    else:
                        # Escape without '\': unknown sequence.
                        kind = '' if kind is None else kind + ';'
                        params = ''.join(params)
                        seq = first + kind + params + '\x1b' + text[index]
                        self.__UnhandledEscSeq(seq, ex=True)
                        return (index+1, None, None)
                break
            if ch == ';' and kind is None:
                # Found end to kind portion of sequence.
                index += 1
                if len(params) == 0:
                    self.__UnhandledEscSeq(first+';', ex=True)
                    return (index, None, None)
                kind = ''.join(params)
                params = []
                continue
            # Character is part of unfinished kind or of parameters.
            params.append(ch)
            index += 1
        # The escape sequence is not complete, inform this to caller by giving
        # '?' as sequence kind and all read text in params.
        kind = '' if kind is None else kind
        params = ''.join(params)
        return (index, '?', kind+params)
    def __HandleEscSeq(self, text, index, csi=False):
        """
        Tries to parse escape sequence from input and if its not complete then
        puts it in unparsedInput and process it when the ProcessInput called
        next time.
        """
        if csi or text[index] == '[':
            # Traditional escape sequences.
            if csi:
                firstChar = '['
            else:
                firstChar = text[index]
                index += 1
            index, finalChar, interChars = self.__ParseEscSeq(text, index)
            if finalChar == '?':
                # Partial sequence; save and parse later.
                self.unparsedInput = "\x1b" + firstChar
                if interChars != None:
                    self.unparsedInput += interChars
                return index
            if finalChar in self.escSeqHandlers.keys():
                # Complete sequence with handler.
                try:
                    self.escSeqHandlers[finalChar](firstChar, interChars, finalChar)
                except:
                    glsLog.add("TE: Exception in ESC seq handler for '[%s%s'!\n%s"%
                               (interChars, finalChar, traceback.format_exc()))
                return index
            # Unhandled sequence.
            escSeq = "["
            if interChars != None:
                escSeq += interChars
            escSeq += finalChar
            self.__UnhandledEscSeq(escSeq)
            return index
        if text[index] == ']':
            # Extended escape sequences used by Xterm and modern terminals.
            firstChar = text[index]
            index += 1
            index, kind, params = self.__ParseExtendedSeq(firstChar, text, index)
            if kind is None:
                # Unhandled sequence (already notified logger).
                return index
            if kind == '?':
                # Partial sequence; save and parse later.
                self.unparsedInput = "\x1b" + firstChar + params
                return index
            if kind not in self.exHandlers:
                params = '' if params is None else params
                escSeq = firstChar + kind + ';' + params
                self.__UnhandledEscSeq(escSeq, ex=True)
                return index
            try:
                self.exHandlers[kind](firstChar, params)
            except:
                params = '' if params is None else params
                glsLog.add("TE: Exception in EX handler for ']%s%s'!\n%s"%
                           (kind, params, traceback.format_exc()))
            return index
        if text[index] == 'P':
            # Additional extended escape sequences.
            # !!avose: TODO
            index += 1
            textlen = len(text)
            while index < textlen:
                if text[index] == '\x1b' or text[index] == '\x07':
                    return index + 1
                index += 1
            return index
        # Escape but non-CSI sequences.
        if text[index] in self.escHandlers:
            try:
                self.escHandlers[text[index]]()
            except:
                glsLog.add("TE: Exception in ESC handler for '[%s%s'!\n%s"%
                           (interChars, finalChar, traceback.format_exc()))
        else:
            self.__UnhandledEscSeq(text[index])
        return index + 1
    def __SaveCursor(self):
        ndx = 1 if self.modes[self.MODE_ALTBUF] else 0
        self.savedCursor[ndx] = (self.curY, self.curX, self.cursorStyle, self.curRendition)
        glsLog.debug("TE: Save Cursor: %d,%d [%s]"%
                     (self.curY, self.curX, 'ALT' if ndx == 1 else 'PRI'), 3)
        return
    def __RestoreCursor(self):
        ndx = 1 if self.modes[self.MODE_ALTBUF] else 0
        self.curY, self.curX, self.cursorStyle, self.curRendition = self.savedCursor[ndx]
        self.curX = min(max(self.curX, 0), self.cols-1)
        self.curY = min(max(self.curY, 0), self.rows-1)
        glsLog.debug("TE: Restore Cursor: %d,%d [%s]"%
                     (self.curY, self.curX, 'ALT' if ndx == 1 else 'PRI'), 3)
        return
    def __AltBuffIn(self, save=False, clear=False):
        if self.modes[self.MODE_ALTBUF]:
            return
        if save:
            self.__SaveCursor()
        self.modes[self.MODE_ALTBUF] = True
        self.savedScreen, self.screen = self.screen, self.savedScreen
        self.savedRendition, self.scrRendition = self.scrRendition, self.savedRendition
        self.Resize(self.rows, self.cols)
        if clear:
            self.Clear()
        glsLog.debug("TE: (ALTBUF) Enter: save=%s clear=%s"%
                     (str(save), str(clear)), 3)
        return
    def __AltBuffOut(self, restore=False, clear=False):
        if not self.modes[self.MODE_ALTBUF]:
            return
        self.modes[self.MODE_ALTBUF] = False
        if clear:
            self.Clear()
        self.savedScreen, self.screen = self.screen, self.savedScreen
        self.savedRendition, self.scrRendition = self.scrRendition, self.savedRendition
        self.Resize(self.rows, self.cols)
        if restore:
            self.__RestoreCursor()
        glsLog.debug("TE: (ALTBUF) Exit: restore=%s clear=%s"%
                     (str(restore), str(clear)), 3)
        return
    def __SetRenditionBits(self, style=None, fg=None, bg=None):
        mask = 0
        bits = 0
        if style is not None:
            flag, enable = style
            mask |= 0xffff
            if enable:
                bits |=  0xffff &  flag
            else:
                bits &= ~0xffff | ~flag
        if fg is not None:
            mask |= (0xff)      << 16
            bits |= (0xff & fg) << 16
        if bg is not None:
            mask |= (0xff)      << 24
            bits |= (0xff & bg) << 24
        self.curRendition = (self.curRendition & mask) | bits
        return
    ################################################################
    # Character Handlers
    ################################################################
    def __OnCharBS(self, text, index):
        """
        Handler for backspace character
        """
        glsLog.debug("TE: BS: @ (%d,%d)"%(self.curY, self.curX), 3)
        if self.curX > 0:
            self.curX -= 1
        return index + 1
    def __OnCharHT(self, text, index):
        """
        Handler for horizontal tab character
        """
        glsLog.debug("TE: TAB: @ (%d,%d)"%(self.curY, self.curX), 3)
        while self.curX + 1 < self.cols:
            self.curX += 1
            if self.curX % 8 == 0:
                break
        return index + 1
    def __OnCharLF(self, text, index):
        """
        Handler for line feed character
        """
        glsLog.debug("TE: LF: @ (%d,%d)"%(self.curY, self.curX), 3)
        self.__NewLine()
        return index + 1
    def __OnCharCR(self, text, index):
        """
        Handler for carriage return character
        """
        glsLog.debug("TE: CR: @ (%d,%d)"%(self.curY, self.curX), 3)
        self.curX = 0
        return index + 1
    def __OnCharXON(self, text, index):
        """
        Handler for XON character
        """
        glsLog.debug("TE: XON: @ (%d,%d)"%(self.curY, self.curX), 3)
        self.ignoreChars = False
        return index + 1
    def __OnCharXOFF(self, text, index):
        """
        Handler for XOFF character
        """
        glsLog.debug("TE: XOFF: @ (%d,%d)"%(self.curY, self.curX), 3)
        self.ignoreChars = True
        return index + 1
    def __OnCharESC(self, text, index):
        """
        Handler for escape character
        """
        index += 1
        if index < len(text):
            index = self.__HandleEscSeq(text, index)
        else:
            glsLog.debug("TE: ESC: @ (%d,%d) without sequence!"%
                         (self.curY, self.curX), 1)
        return index
    def __OnCharCSI(self, text, index):
        """
        Handler for control sequence intruducer(CSI) character
        """
        glsLog.debug("TE: CSI Character!", 1)
        index += 1
        if index < len(text):
            index = self.__HandleEscSeq(text, index, csi=True)
        else:
            glsLog.debug("TE: CSI: @ (%d,%d) without sequence!"%
                         (self.curY, self.curX), 1)
        return index
    def __OnCharSO(self, text, index):
        """
        Handler SO: Shift out to the G1 character set.
        """
        glsLog.debug("TE: (SO) Shift Out: Unimplemented.", 10)
        return index + 1
    def __OnCharSI(self, text, index):
        """
        Handler SI: Shift in to the G0 character set.
        """
        glsLog.debug("TE: (SI) Shift In: Unimplemented.", 10)
        return index + 1
    def __OnCharIgnore(self, text, index):
        """
        Handler: dummy for unhandled characters
        """
        return index + 1
    ################################################################
    # Mode Enter / Exit Handlers
    ################################################################
    def __OnModeALTBUF(self, enable):
        if enable:
            self.__AltBuffIn(save=False, clear=False)
        else:
            self.__AltBuffOut(restore=False, clear=False)
        return
    def __OnModeALTBUF_SCO(self, enable):
        if enable:
            self.__AltBuffIn(save=True, clear=False)
        else:
            self.__AltBuffOut(restore=True, clear=True)
        return
    def __OnModeALTBUF_SCR(self, enable):
        if enable:
            if not self.modes[self.MODE_ALTB_CSR]:
                self.SaveCursor()
        else:
            if self.modes[self.MODE_ALTB_CSR]:
                self.RestoreCursor()
        return
    def __OnModeALTBUF_SCI(self, enable):
        if enable:
            self.__AltBuffIn(save=True, clear=True)
        else:
            self.__AltBuffOut(restore=True, clear=False)
        return
    ################################################################
    # Escape Sequence Handlers
    ################################################################
    def __OnEscSeqICH_SL(self, first, params, last):
        # Handler ICH / SL: Insert (Blank) Characters / Shift Left
        if ' ' in params:
            # Escape sequence SL
            # !!avose: This is almost certainly wrong..
            glsLog.debug("TE: (SL) Shift Left: '%s%s'"%(params, last), 3)
            plist = params.split(' ')
            if len(plist) != 2:
                self.__UnhandledEscSeq(first+params+last)
                return
            count = int(plist[0]) if plist[0] != '' else 1
            newX = self.curX + count
            self.curX = newX if newX < self.cols else self.cols
        else:
            # Escape sequence ICH
            glsLog.debug("TE: (ICH) Insert (Blank) Chars: '%s%s'"%(params, last), 3)
            row = self.curY
            col = self.curX
            count = int(params) if params != '' else 1
            count = min(count, self.cols-col)
            for i in range(count):
                for c in reversed(range(col, self.cols-1)):
                    self.screen[row][c+1] = self.screen[row][c]
                    self.scrRendition[row][c+1] = self.scrRendition[row][c]
                self.screen[row][col] = ' '
                self.scrRendition[row][col] = self.curRendition
        return
    def __OnEscSeqCUU(self, first, params, last):
        # Handler CUU: Cursor Update Up
        glsLog.debug("TE: (CUU) Cursor Update Up: '%s%s'"%(params, last), 3)
        n = 1
        if params != None:
            n = int(params)
        self.curY -= n;
        if self.curY < 0:
            self.curY = 0
        return
    def __OnEscSeqCUD(self, first, params, last):
        # Handler CUD: Cursor Update Down
        glsLog.debug("TE: (CUD) Cursor Update Down: '%s%s'"%(params, last), 3)
        n = 1
        if params != None:
            n = int(params)
        self.curY += n;
        if self.curY >= self.rows:
            self.curY = self.rows - 1
        return
    def __OnEscSeqCUF(self, first, params, last):
        # Handler CUF: Cursor Update Forward
        glsLog.debug("TE: (CUF) Cursor Update Forward: '%s%s'"%(params, last), 3)
        n = 1
        if params != None:
            n = int(params)
        self.curX += n;
        if self.curX >= self.cols:
            self.curX = self.cols - 1
        return
    def __OnEscSeqCUB(self, first, params, last):
        # Handler CUB: Cursor Update Back
        glsLog.debug("TE: (CUB) Cursor Update Back: '%s%s'"%(params, last), 3)
        n = 1
        if params != None:
            n = int(params)
        self.curX -= n;
        if self.curX < 0:
            self.curX = 0
        return
    def __OnEscSeqCHA(self, first, params, last):
        # Handler CHA: Cursor Horizontal Absolute Position
        if params == None:
            glsLog.debug("TE: (CHA) Cursor Horizontal Position: No Parameter!", 3)
            return
        col = int(params) - 1
        if col >= 0 and col < self.cols:
            self.curX = col
        else:
            glsLog.debug("TE: (CHA) Cursor Horizontal Position: %d out of bounds (%d)!"%
                         (col, self.cols), 1)
        glsLog.debug("TE: (CHA) Cursor Horizontal Absolute: %d"%(col), 3)
        return
    def __OnEscSeqCUP(self, first, params, last):
        # Handler CUP: Cursor Update Position
        y = 0
        x = 0
        if params != None:
            values = params.split(';')
            if len(values) == 2:
                y = int(values[0]) - 1
                x = int(values[1]) - 1
                glsLog.debug("TE: (CUP) Cursor Update Position: (%d,%d)"%(y, x), 3)
            else:
                glsLog.debug("TE: (CUP) Cursor Position: Invalid Parameters '%s%s'!"%
                             (params, last), 1)
                return
        x = min(max(x, 0), self.cols-1)
        y = min(max(y, 0), self.rows-1)
        self.curX = x
        self.curY = y
        return
    def __OnEscSeqED(self, first, params, last):
        # Handler ED: Erase Display
        n = 0
        if params != None:
            n = int(params)
        if n == 0:
            self.ClearRect(self.curY, self.curX, self.rows - 1, self.cols - 1)
            glsLog.debug("TE: (ED) Erase Display: (%d,%d) to (%d,%d)"%
                         (self.curY, self.curX, self.rows - 1, self.cols - 1), 3)
        elif n == 1:
            self.ClearRect(0, 0, self.curY, self.curX)
            glsLog.debug("TE: (ED) Erase Display: (%d,%d) to (%d,%d)"%
                         (0, 0, self.curY, self.curX), 3)
        elif n == 2 or n == 3:
            self.ClearRect(0, 0, self.rows - 1, self.cols - 1)
            glsLog.debug("TE: (ED) Erase Display: (%d,%d) to (%d,%d)"%
                         (0, 0, self.rows - 1, self.cols - 1), 3)
        else:
            glsLog.debug("TE: (ED) Erase Display: Invalid Parameter %d!"%(n), 1)
        return
    def __OnEscSeqEL(self, first, params, last):
        # Handler EL: Erase Line
        n = 0
        if params != None:
            n = int(params)
        if n == 0:
            self.ClearRect(self.curY, self.curX, self.curY, self.cols - 1)
            glsLog.debug("TE: (EL) Erase Line: (%d,%d) to (%d,%d)"%
                         (self.curY, self.curX, self.curY, self.cols - 1), 3)
        elif n == 1:
            self.ClearRect(self.curY, 0, self.curY, self.curX)
            glsLog.debug("TE: (EL) Erase Line: (%d,%d) to (%d,%d)"%
                         (self.curY, 0, self.curY, self.curX), 3)
        elif n == 2:
            self.ClearRect(self.curY, 0, self.curY, self.cols - 1)
            glsLog.debug("TE: (EL) Erase Line: (%d,%d) to (%d,%d)"%
                         (self.curY, 0, self.curY, self.cols - 1), 3)
        else:
            glsLog.debug("TE: (EL) Erase Line: Invalid Parameter %d!"%(n), 1)
        return
    def __OnEscSeqIL(self, first, params, last):
        # Handler IL: Insert Lines
        if self.curY > self.scrollRegion[1]:
            return
        self.curX = 0
        n = int(params) if params != None else 1
        for l in range(n):
            line = self.screen.pop(self.scrollRegion[1])
            for i in range(self.cols):
                line[i] = u' '
            self.screen.insert(self.curY, line)
            rendition = self.scrRendition.pop(self.scrollRegion[1])
            for i in range(self.cols):
                rendition[i] = self.curRendition
            self.scrRendition.insert(self.curY, rendition)
        glsLog.debug("TE: (IL) Insert Lines: %d @ (%d,%d) term.rows=%d"%
                     (n, self.curY, self.scrollRegion[1], self.rows), 3)
        return
    def __OnEscSeqDL(self, first, params, last):
        # Handler DL: Delete Lines
        if self.curY > self.scrollRegion[1]:
            return
        self.curX = 0
        n = int(params) if params != None else 1
        for l in range(n):
            line = self.screen.pop(self.curY)
            for i in range(self.cols):
                line[i] = u' '
            self.screen.insert(self.scrollRegion[1], line)
            rendition = self.scrRendition.pop(self.curY)
            for i in range(self.cols):
                rendition[i] = self.curRendition
            self.scrRendition.insert(self.scrollRegion[1], rendition)
        glsLog.debug("TE: (DL) Delete Lines: %d @ (%d,%d) term.rows=%d"%
                     (n, self.curY, self.scrollRegion[1], self.rows), 3)
        return
    def __OnEscSeqDCH(self, first, params, last):
        # Handler DCH: Delete Characters
        n = int(params) if params != None else 1
        for c in range(self.curX,self.cols):
            if c + n < self.cols:
                self.screen[self.curY][c] = self.screen[self.curY][c+n]
                self.scrRendition[self.curY][c] = self.scrRendition[self.curY][c+n]
            else:
                self.screen[self.curY][c] = ' '
                self.scrRendition[self.curY][c] = 0
        glsLog.debug("TE: (DCH) Delete Characters: %d @ (%d,%d)"%
                     (n, self.curY, self.curX), 3)
        return
    def __OnEscSeqVPA(self, first, params, last):
        # Handler VPA: Cursor Vertical Position Absolute
        if params == None:
            glsLog.debug("TE: (VPA) Cursor Vertical Position: No Parameter!", 1)
            return
        row = int(params) - 1
        if row >= 0 and row < self.rows:
            self.curY = row
        else:
            glsLog.debug("TE: (VPA) Cursor Vertical Position: %d out of bounds!"%
                         (row), 1)
        glsLog.debug("TE: (VPA) Cursor Vertical Position: %d"%(row), 3)
        return
    def __OnEscSeqSGR(self, first, params, last):
        # Handler SGR: Select Graphic Rendition
        if params is None:
            self.curRendition = 0
            glsLog.debug("TE: (SGR) Select Graphic Rendition: No Parameter; Reset.", 3)
            return
        if '?' in params or '>' in params or '%' in params:
            self.__UnhandledEscSeq(first+params+last)
            return
        if (params.startswith("38:5:") or params.startswith("38;5:") or
            params.startswith("38;5;") or params.startswith("48:5:") or
            params.startswith("48;5:") or params.startswith("48;5;")):
            orig_params = params
            params = params.replace(':',';')
            params = params.split(';')
            if len(params) != 3:
                glsLog.debug("TE: (SGR) Select Graphic Rendition: Unsupported: '%s'."%
                             (orig_params), 1)
                return
            fg = True if params[0] == '38' else False
            color = int(params[2])
            if fg:
                self.__SetRenditionBits(fg=color)
            else:
                self.__SetRenditionBits(bg=color)
            glsLog.debug("TE: (SGR) Select Graphic Rendition: %s Color-256: %s."%
                         ('FG' if fg else 'BG', color), 3)
            return
        renditions = params.split(';')
        for rendition in renditions:
            irendition = int(rendition)
            if irendition == 0:
                # reset rendition
                self.curRendition = 0
            elif irendition > 0 and irendition < 9:
                # style
                self.__SetRenditionBits(style=(1<<(irendition-1), True))
            elif irendition >= 30 and irendition <= 37:
                # foreground
                self.__SetRenditionBits(fg=(irendition-30))
            elif irendition >= 40 and irendition <= 47:
                # background
                self.__SetRenditionBits(bg=(irendition-40))
            elif irendition == 27:
                # reverse video off
                self.__SetRenditionBits(style=(self.RENDITION_STYLE_INVERSE, False))
            elif irendition == 39:
                # set underline off, set default foreground color
                self.__SetRenditionBits(style=(self.RENDITION_STYLE_UNDERLINE, False), fg=0)
            elif irendition == 49:
                # set default background color
                self.__SetRenditionBits(bg=0)
            else:
                glsLog.debug("TE: (SGR) Select Graphic Rendition: Unsupported %d"%
                             (irendition), 1)
                pass
        glsLog.debug("TE: (SGR) Select Graphic Rendition: '%s'"%(first+params+last), 5)
        return
    def __OnEscSeqDSR(self, first, params, last):
        # Handler DSR: Device Status Report
        if params is None or params == "":
            glsLog.debug("TE: (DSR) Device Status Report: No Parameter!", 1)
            return
        if params.startswith('?'):
            params = params[1:]
        param = int(params)
        if param == 5:
            reply = '\x1b[0n'
        elif param == 6:
            reply = '\x1b[%d;%dR'%(self.curY, self.curX)
        else:
            self.__UnhandledEscSeq(first+params+last)
            return
        self.__Callback(self.CALLBACK_SEND_DATA, reply)
        glsLog.debug("TE: (DSR) Device Status Report: '%s' reply='%s'"%
                     (first+params+last, reply), 3)
        return
    def __OnEscSeqSMRM(self, first, params, last, enable):
        if enable:
            label = "(SM) Set Mode"
        else:
            label = "(RM) Reset Mode"
        if params == None or params == '':
            glsLog.debug("TE: %s: No Parameter!"%(label), 1)
            return
        if params.startswith('?'):
            params = params[1:]
            prefix = '?'
        else:
            prefix = ''
        for param in params.split(';'):
            param = prefix + param
            if param not in self.modes:
                glsLog.debug("TE: %s: Unknown Mode: '%s'!"%(label, param), 1)
                continue
            if param in self.modeHandlers:
                self.modeHandlers[param](enable)
            self.modes[param] = enable
        self.__Callback(self.CALLBACK_UPDATE_MODE, self.modes)
        glsLog.debug("TE: %s: '%s'"%(label, first+params+last), 3)
        return
    def __OnEscSeqSM(self, first, params, last):
        # Handler SM: Sets Mode
        self.__OnEscSeqSMRM(first, params, last, True)
        return
    def __OnEscSeqRM(self, first, params, last):
        # Handler RM: Resets Mode
        self.__OnEscSeqSMRM(first, params, last, False)
        return
    def __OnEscSeqDECSCUSR(self, first, params, last):
        # Handler DECSCUSR: Set Cursor Style
        if params is None:
            glsLog.debug("TE: (DECSCUSR) Cursor Style: No Parameter!", 1)
            return
        if len(params) > 2 or not params.endswith(' '):
            self.__UnhandledEscSeq(first+params+last)
            return
        params = params.strip()
        style = int(params) if params else 0
        if style == 0 or style not in range(1, 7):
            style = self.CURSOR_STYLE_DEFAULT
        elif style == 1 or style == 2:
            style = self.CURSOR_STYLE_BLOCK
        elif style == 3 or style == 4:
            style = self.CURSOR_STYLE_UNDERLINE
        elif style == 5 or style == 6:
            style = self.CURSOR_STYLE_BAR
        if style != self.cursorStyle:
            self.cursorStyle = style
            self.__Callback(self.CALLBACK_UPDATE_CURSOR, self.cursorStyle)
        glsLog.debug("TE: (DECSCUSR) Cursor Style: %d"%(style), 3)
        return
    def __OnEscSeqDECSTBM(self, first, params, last):
        # Handler DECSTBM: Set Top / Bottom Margins (Scroll Region)
        if params == None:
            glsLog.debug("TE: (DECSTBM) Top/Bottom Margins: No Parameter!", 1)
            return
        args = params.split(';')
        if len(args) != 2:
            self.__UnhandledEscSeq(first+params+last)
            return
        top, bottom = args
        top = int(top) - 1
        bottom = int(bottom) - 1
        top = max(top, 0)
        bottom = min(bottom, self.cols-1)
        if top >= bottom:
            top = 0
            bottom = self.rows - 1
        self.scrollRegion = (top, bottom)
        self.curX = 0
        self.curY = 0
        glsLog.debug("TE: (DECSTBM) Top/Bottom Margins: (%d,%d) '%s' rows=%d"%
                     (top, bottom, first+params+last, self.rows), 3)
        return
    def __OnEscSeqDA2(self, first, params, last):
        # Handler DA2: Secondary Device Attributes
        reply = '\x1b[>1;' + glsVersion.replace('.','')  + ';0c'
        self.__Callback(self.CALLBACK_SEND_DATA, reply)
        return
    def __OnEscSeqCSZ(self, first, params, last):
        # Handler CSZ: Cursor Style / Size
        if params == None:
            glsLog.debug("TE: (CSZ) Cursor Style: No Parameter!", 1)
            return
        if len(params) != 2 or params[0] != '?':
            if len(params) >= 1 and params[0] == '>':
                self.__OnEscSeqDA2(first, params, last)
                return
            self.__UnhandledEscSeq(first+params+last)
            return
        style = int(params[1])
        if style not in (0, 1, 2, 8):
            style = self.CURSOR_STYLE_DEFAULT
        if style != self.cursorStyle:
            self.cursorStyle = style
            self.__Callback(self.CALLBACK_UPDATE_CURSOR, self.cursorStyle)
        glsLog.debug("TE: (CSZ) Cursor Style: %d"%(style), 3)
        return
    def __OnEscSeqTWS(self, first, params, last):
        # Handler TWS: Terminal Window Settings
        if params == None:
            glsLog.debug("TE: (TWS) Terminal Window Settings: No Parameter!", 1)
            return
        glsLog.debug("TE: (TWS) Not Implemented: '%s'."%(first+params+last), 1)
        return
    ################################################################
    # Escape Handlers (Non-CSI)
    ################################################################
    def __OnEscIND(self):
        # Handler IND: Index (Linefeed)
        glsLog.debug("TE: (IND) Index: @ (%d,%d)"%
                     (self.curY, self.curX), 3)
        self.__NewLine()
        return
    def __OnEscNEL(self):
        # Handler NEL: Next Line
        glsLog.debug("TE: (NEL) Next Line: @ (%d,%d)"%
                     (self.curY, self.curX), 3)
        self.curX = 0
        self.__NewLine()
        return
    def __OnEscRI(self):
        # Handler RI: Reverse Index (LineFeed)
        if self.curY == self.scrollRegion[0]:
            self.ScrollDown()
            return
        if self.curY > self.scrollRegion[0] and self.curY <= self.scrollRegion[1]:
            self.curY -= 1
            return
        if self.curY > 0:
            self.curY -= 1
        return
    def __OnEscDECSC(self):
        # Handler DECSC: Save Cursor
        self.__SaveCursor()
        return
    def __OnEscDECRC(self):
        # Handler DECRC: Restore Cursor
        self.__RestoreCursor()
        return
    def __OnEscDECPNM(self):
        # Handler DECPNM: keyPad Numeric
        glsLog.debug("TE: (DECPNM) keyPad Numeric Mode: Unsupported", 10)
        return
    def __OnEscDECPAM(self):
        # Handler DECPAM: keyPad Application
        glsLog.debug("TE: (DECPAM) keyPad Application Mode: Unsupported", 10)
        return
    ################################################################
    # Extended Escape Sequence Handlers
    ################################################################
    def __OnExICON_TITLE(self):
        # Handler: Window Title
        glsLog.debug("TE: Set Window Title: Unimplemented.", 1)
        #self.__Callback(self.CALLBACK_UPDATE_WINDOW_TITLE, params)
        return

################################################################
