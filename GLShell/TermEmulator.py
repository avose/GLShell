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
# Source code modified beginning in August 2023 by Aaron Vose.
# avose@aaronvose.net

"""
Emulator for VT100 terminal programs.

This module provides terminal emulation for VT100 terminal programs. It handles
V100 special characters and most important escape sequences. It also handles
graphics rendition which specifies text style(i.e. bold, italics), foreground color
and background color. The handled escape sequences are CUU, CUD, CUF, CUB, CHA,
CUP, ED, EL, VPA and SGR.
"""

from __future__ import print_function

import sys
import os
import pty
import select
from array import *

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
    __ASCII_S0 = 14         # Activates G1 character set
    __ASCII_SI = 15         # Activates G0 character set
    __ASCII_XON = 17        # Resume Transmission
    __ASCII_XOFF = 19       # Stop Transmission or Ignore Characters
    __ASCII_ESC = 27        # Escape
    __ASCII_SPACE = 32      # Space
    __ASCII_CSI = 153       # Control Sequence Introducer

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

    __ESCSEQ_SETM = 'h'     # [?] n h: Sets a mode; there are 14 modes defined for a
                            # vt102. While not all modes are supported, some extra
                            # modes commonly used with other terminal types may be
                            # supported.

    __ESCSEQ_CLRM = 'l'     # [?] n l: Clears a mode; there are 14 modes defined for a
                            # vt102. While not all modes are supported, some extra
                            # modes commonly used with other terminal types may be
                            # supported.

    __ESCSEQ_CSR = 'r'      # Multiple escape sequences end in 'r'. One of the more
                            # important ones is the scrolling region: "n ; m r" which
                            # limits effect of scrolling to specified range of lines.

    __ESCSEQ_CSZ = 'c'      # Multiple escape sequences end in 'c'. One of the more
                            # important ones is setting the cursor size / style:
                            # "? n c", where n is the style.

    # vt102 modes.
    MODE_KAM     = '2'    # Keyboard action
    MODE_IRM     = '4'    # Insert-replace
    MODE_SRM     = '12'   # Send-receive
    MODE_LMN     = '20'   # Linefeed / new line
    MODE_DECCKM  = '?1'   # Cursor key
    MODE_DECANM  = '?2'   # ANSI / VT52
    MODE_DECCOLM = '?3'   # Column
    MODE_DECSCLM = '?4'   # Scrolling
    MODE_DECSCNM = '?5'   # Screen
    MODE_DECOM   = '?6'   # Origin
    MODE_DECAWM  = '?7'   # Auto wrap
    MODE_DECARM  = '?8'   # Auto repeat
    MODE_DECPFF  = '?18'  # Print form feed
    MODE_DECPEX  = '?19'  # Print extent
    # xterm modes.
    MODE_DECTCEM = '?25'  # Show cursor
    MODE_BRCKPST = '?2004'# Bracketed paste mode

    CURSOR_STYLE_DEFAULT = 0
    CURSOR_STYLE_INVISIBLE = 1
    CURSOR_STYLE_UNDERLINE = 2
    CURSOR_STYLE_BLOCK = 8
    
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
    CALLBACK_MODE_CHANGE = 4
    CALLBACK_CURSOR_CHANGE = 5

    def __init__(self, rows, cols):
        """
        Initializes the terminal with specified rows and columns. User can
        resize the terminal any time using Resize method. By default the screen
        is cleared(filled with blank spaces) and cursor positioned in the first
        row and first column with the entire scrren in the scroll region.
        """
        self.cols = cols
        self.rows = rows
        self.curX = 0
        self.curY = 0
        self.ignoreChars = False
        self.scrollRegion = (0, self.rows-1)

        # special character handlers
        self.charHandlers = { self.__ASCII_NUL :self.__OnCharIgnore,
                              self.__ASCII_BEL :self.__OnCharIgnore,
                              self.__ASCII_BS  :self.__OnCharBS,
                              self.__ASCII_HT  :self.__OnCharHT,
                              self.__ASCII_LF  :self.__OnCharLF,
                              self.__ASCII_VT  :self.__OnCharLF,
                              self.__ASCII_FF  :self.__OnCharLF,
                              self.__ASCII_CR  :self.__OnCharCR,
                              self.__ASCII_XON :self.__OnCharXON,
                              self.__ASCII_XOFF:self.__OnCharXOFF,
                              self.__ASCII_ESC :self.__OnCharESC,
                              self.__ASCII_CSI :self.__OnCharCSI,
                              self.__ASCII_S0 :self.__OnCharS0,
                              self.__ASCII_SI :self.__OnCharSI, }

        # escape sequence handlers
        self.escSeqHandlers = { self.__ESCSEQ_ICH_SL:self.__OnEscSeqICH_SL,
                                self.__ESCSEQ_CUU   :self.__OnEscSeqCUU,
                                self.__ESCSEQ_CUD   :self.__OnEscSeqCUD,
                                self.__ESCSEQ_CUF   :self.__OnEscSeqCUF,
                                self.__ESCSEQ_CUB   :self.__OnEscSeqCUB,
                                self.__ESCSEQ_CHA   :self.__OnEscSeqCHA,
                                self.__ESCSEQ_CUP   :self.__OnEscSeqCUP,
                                self.__ESCSEQ_ED    :self.__OnEscSeqED,
                                self.__ESCSEQ_EL    :self.__OnEscSeqEL,
                                self.__ESCSEQ_IL    :self.__OnEscSeqIL,
                                self.__ESCSEQ_DL    :self.__OnEscSeqDL,
                                self.__ESCSEQ_DCH   :self.__OnEscSeqDCH,
                                self.__ESCSEQ_VPA   :self.__OnEscSeqVPA,
                                self.__ESCSEQ_SGR   :self.__OnEscSeqSGR,
                                self.__ESCSEQ_SETM  :self.__OnEscSeqSETCLRM,
                                self.__ESCSEQ_CLRM  :self.__OnEscSeqSETCLRM,
                                self.__ESCSEQ_CSR   :self.__OnEscSeqCSR,
                                self.__ESCSEQ_CSZ   :self.__OnEscSeqCSZ, }

        # cursor styles.
        self.cursorStyle = self.CURSOR_STYLE_DEFAULT

        # terminal modes.
        self.modes = { self.MODE_DECTCEM:True,
                       self.MODE_BRCKPST:False, }

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

        # list of dirty lines since last call to GetDirtyLines
        self.isLineDirty = []

        for i in range(rows):
            line = array('u')
            rendition = array('L')

            for j in range(cols):
                line.append(u' ')
                rendition.append(0)

            self.screen.append(line)
            self.scrRendition.append(rendition)
            self.isLineDirty.append(False)

        # initializes callbacks
        self.callbacks = { self.CALLBACK_SCROLL_UP_SCREEN: None,
                           self.CALLBACK_UPDATE_LINES: None,
                           self.CALLBACK_UPDATE_CURSOR_POS: None,
                           self.CALLBACK_UPDATE_WINDOW_TITLE: None,
                           self.CALLBACK_MODE_CHANGE: None,
                           self.CALLBACK_CURSOR_CHANGE: None, }

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
        if rows < self.rows:
            # remove rows at top
            for i in range(self.rows - rows):
                self.isLineDirty.pop(0)
                self.screen.pop(0)
                self.scrRendition.pop(0)
        elif rows > self.rows:
            # add blank rows at bottom
            for i in range(rows - self.rows):
                line = array('u')
                rendition = array('L')
                for j in range(self.cols):
                    line.append(u' ')
                    rendition.append(0)
                self.screen.append(line)
                self.scrRendition.append(rendition)
                self.isLineDirty.append(False)
        self.rows = rows
        if cols < self.cols:
            # remove cols at right
            for i in range(self.rows):
                self.screen[i] = self.screen[i][:cols - self.cols]
                for j in range(self.cols - cols):
                    self.scrRendition[i].pop(len(self.scrRendition[i]) - 1)
        elif cols > self.cols:
            # add cols at right
            for i in range(self.rows):
                for j in range(cols - self.cols):
                    self.screen[i].append(u' ')
                    self.scrRendition[i].append(0)
        self.cols = cols
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
            if end + 1 > start:
                self.isLineDirty[i] = True
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
        style = self.scrRendition[row][col] & 0x000000ff
        fgcolor = (self.scrRendition[row][col] & 0x00000f00) >> 8
        bgcolor = (self.scrRendition[row][col] & 0x0000f000) >> 12
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
    def GetDirtyLines(self):
        """
        Returns list of dirty lines(line nos) since last call to GetDirtyLines.
        The line no will be 0..rows - 1.
        """
        dirtyLines = []
        for i in range(self.rows):
            if self.isLineDirty[i]:
                dirtyLines.append(i)
                self.isLineDirty[i] = False
        return dirtyLines
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

        CALLBACK_MODE_CHANGE
            Called whenever a terminal mode has changed. A dictionary of modes
            and their settings (True/False) will be passed as an argument.

        CALLBACK_CURSOR_CHANGE
            Called whenever a the cursor has changed. The new style will be
            passed as an argument.
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
            else:
                if ch in self.printableChars:
                    self.__PushChar(ch)
                else:
                    glsLog.debug("TE WARNING: Unsupported character '%s' = %d"%(ch, ascii), 2)
                    pass
                index += 1
        # update the dirty lines
        if self.callbacks[self.CALLBACK_UPDATE_LINES] != None:
            self.callbacks[self.CALLBACK_UPDATE_LINES]()
        # update cursor position
        if self.callbacks[self.CALLBACK_UPDATE_CURSOR_POS] != None:
            self.callbacks[self.CALLBACK_UPDATE_CURSOR_POS]()
        return
    def ScrollUp(self):
        """
        Scrolls up the terminal screen by one line. The callbacks
        CALLBACK_UPDATE_LINES and CALLBACK_SCROLL_UP_SCREEN are called before
        scrolling the screen.
        """
        if self.scrollRegion[0] == 0 and self.scrollRegion[1] == self.rows-1:
            # update the dirty lines
            if self.callbacks[self.CALLBACK_UPDATE_LINES] != None:
                self.callbacks[self.CALLBACK_UPDATE_LINES]()
            # scrolls up the screen
            if self.callbacks[self.CALLBACK_SCROLL_UP_SCREEN] != None:
                self.callbacks[self.CALLBACK_SCROLL_UP_SCREEN]()
        line = self.screen.pop(self.scrollRegion[0])
        for i in range(self.cols):
            line[i] = u' '
        self.screen.insert(self.scrollRegion[1], line)
        rendition = self.scrRendition.pop(self.scrollRegion[0])
        for i in range(self.cols):
            rendition[i] = 0
        self.scrRendition.insert(self.scrollRegion[1], rendition)
        return
    def Dump(self, file=sys.stdout):
        """
        Dumps the entire terminal screen into the given file/stdout
        """
        for i in range(self.rows):
            file.write(self.screen[i].tostring())
            file.write("\n")
        return
    def __NewLine(self):
        """
        Moves the cursor to the next line, if the cursor is already at the
        bottom row then scroll up.
        """
        self.curX = 0
        if self.curY + 1 < self.rows:
            self.curY += 1
        else:
            self.ScrollUp()
        return
    def __PushChar(self, ch):
        """
        Writes the character(ch) into current cursor position and advances
        cursor position.
        """
        if self.curX >= self.cols:
            self.__NewLine()
        self.screen[self.curY][self.curX] = ch
        self.scrRendition[self.curY][self.curX] = self.curRendition
        self.curX += 1
        self.isLineDirty[self.curY] = True
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
                glsLog.debug("TE WARNING: Unexpected characters in escape sequence %s"%ch, 2)
            index += 1
        # the escape sequence is not complete, inform this to caller by giving
        # '?' as final char
        return (index, '?', interChars)
    def __UnhandledEscSeq(self, seq):
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
        glsLog.debug("TE WARNING: Unhandled ESC seq '%s'"%printable_seq, 2)
        return
    def __HandleEscSeq(self, text, index):
        """
        Tries to parse escape sequence from input and if its not complete then
        puts it in unparsedInput and process it when the ProcessInput called
        next time.
        """
        if text[index] == '[':
            index += 1
            index, finalChar, interChars = self.__ParseEscSeq(text, index)
            if finalChar == '?':
                self.unparsedInput = "\033["
                if interChars != None:
                    self.unparsedInput += interChars
            elif finalChar in self.escSeqHandlers.keys():
                self.escSeqHandlers[finalChar](interChars, finalChar)
            else:
                escSeq = "["
                if interChars != None:
                    escSeq += interChars
                escSeq += finalChar
                __UnhandledEscSeq(escSeq)
        elif text[index] == ']':
            textlen = len(text)
            if index + 2 < textlen:
                if text[index + 1] == '0' and text[index + 2] == ';':
                    # parse title, terminated by bell char(\007)
                    index += 3 # ignore '0' and ';'
                    start = index
                    while index < textlen:
                        if ord(text[index]) == self.__ASCII_BEL:
                            break
                        index += 1
                    self.__OnEscSeqTitle(text[start:index])
        else:
            __UnhandledEscSeq(text[index])
            index += 1
        return index
    def __OnCharBS(self, text, index):
        """
        Handler for backspace character
        """
        if self.curX > 0:
            self.curX -= 1
        return index + 1
    def __OnCharHT(self, text, index):
        """
        Handler for horizontal tab character
        """
        while self.curX + 1 < self.cols:
            self.curX += 1
            if self.curX % 8 == 0:
                break
        return index + 1
    def __OnCharLF(self, text, index):
        """
        Handler for line feed character
        """
        self.__NewLine()
        return index + 1
    def __OnCharCR(self, text, index):
        """
        Handler for carriage return character
        """
        self.curX = 0
        return index + 1
    def __OnCharXON(self, text, index):
        """
        Handler for XON character
        """
        self.ignoreChars = False
        return index + 1
    def __OnCharXOFF(self, text, index):
        """
        Handler for XOFF character
        """
        self.ignoreChars = True
        return index + 1
    def __OnCharESC(self, text, index):
        """
        Handler for escape character
        """
        index += 1
        if index < len(text):
            index = self.__HandleEscSeq(text, index)
        return index
    def __OnCharCSI(self, text, index):
        """
        Handler for control sequence intruducer(CSI) character
        """
        glsLog.debug("TE WARNING: CSI character.", 2)
        index += 1
        index = self.__HandleEscSeq(text, index)
        return index
    def __OnCharS0(self, text, index):
        """
        Handler for control sequence S0 character
        """
        __UnhandledEscSeq(text[index])
        index += 1
        return index
    def __OnCharSI(self, text, index):
        """
        Handler for control sequence S0 character
        """
        __UnhandledEscSeq(text[index])
        index += 1
        return index
    def __OnCharIgnore(self, text, index):
        """
        Dummy handler for unhandler characters
        """
        return index + 1
    def __OnEscSeqTitle(self, params):
        """
        Handler for window title escape sequence
        """
        if self.callbacks[self.CALLBACK_UPDATE_WINDOW_TITLE] != None:
            self.callbacks[self.CALLBACK_UPDATE_WINDOW_TITLE](params)
        return
    def __OnEscSeqICH_SL(self, params, end):
        """
        Handler for escape sequence ICH and SL
        """
        if ' ' in params:
            # Escape sequence SL
            plist = params.split(' ')
            if len(plist) != 2:
                __UnhandledEscSeq(params+end)
                return
            count = int(plist[0]) if plist[0] != '' else 1
            newX = self.curX + count
            self.curX = newX if newX < self.cols else self.cols
        else:
            # Escape sequence ICH
            count = int(params) if params != '' else 1
            self.__PushChar(' ')
        return
    def __OnEscSeqCUU(self, params, end):
        """
        Handler for escape sequence CUU
        """
        n = 1
        if params != None:
            n = int(params)
        self.curY -= n;
        if self.curY < 0:
            self.curY = 0
        return
    def __OnEscSeqCUD(self, params, end):
        """
        Handler for escape sequence CUD
        """
        n = 1
        if params != None:
            n = int(params)
        self.curY += n;
        if self.curY >= self.rows:
            self.curY = self.rows - 1
        return
    def __OnEscSeqCUF(self, params, end):
        """
        Handler for escape sequence CUF
        """
        n = 1
        if params != None:
            n = int(params)
        self.curX += n;
        if self.curX >= self.cols:
            self.curX = self.cols - 1
        return
    def __OnEscSeqCUB(self, params, end):
        """
        Handler for escape sequence CUB
        """
        n = 1
        if params != None:
            n = int(params)
        self.curX -= n;
        if self.curX < 0:
            self.curX = 0
        return
    def __OnEscSeqCHA(self, params, end):
        """
        Handler for escape sequence CHA
        """
        if params == None:
            glsLog.debug("TE WARNING: CHA without parameter", 2)
            return
        col = int(params)
        # convert it to zero based index
        col -= 1
        if col >= 0 and col < self.cols:
            self.curX = col
        else:
            glsLog.debug("TE WARNING: CHA column out of boundary", 2)
        return
    def __OnEscSeqCUP(self, params, end):
        """
        Handler for escape sequence CUP
        """
        y = 0
        x = 0
        if params != None:
            values = params.split(';')
            if len(values) == 2:
                y = int(values[0]) - 1
                x = int(values[1]) - 1
            else:
                glsLog.debug("TE WARNING: escape sequence CUP has invalid parameters", 2)
                return
        if x < 0:
            x = 0
        elif x >= self.cols:
            x = self.cols - 1
        if y < 0:
            y = 0
        elif y >= self.rows:
            y = self.rows - 1
        self.curX = x
        self.curY = y
        return
    def __OnEscSeqED(self, params, end):
        """
        Handler for escape sequence ED
        """
        n = 0
        if params != None:
            n = int(params)
        if n == 0:
            self.ClearRect(self.curY, self.curX, self.rows - 1, self.cols - 1)
        elif n == 1:
            self.ClearRect(0, 0, self.curY, self.curX)
        elif n == 2:
            self.ClearRect(0, 0, self.rows - 1, self.cols - 1)
        else:
            glsLog.debug("TE WARNING: escape sequence ED has invalid parameter", 2)
        return
    def __OnEscSeqEL(self, params, end):
        """
        Handler for escape sequence EL
        """
        n = 0
        if params != None:
            n = int(params)
        if n == 0:
            self.ClearRect(self.curY, self.curX, self.curY, self.cols - 1)
        elif n == 1:
            self.ClearRect(self.curY, 0, self.curY, self.curX)
        elif n == 2:
            self.ClearRect(self.curY, 0, self.curY, self.cols - 1)
        else:
            glsLog.debug("TE WARNING: escape sequence EL has invalid parameter", 2)
        return
    def __OnEscSeqIL(self, params, end):
        """
        Handler for escape sequence IL
        """
        self.curX = 0
        n = int(params) if params != None else 1
        for l in range(n):
            self.isLineDirty[self.scrollRegion[1]] = True
            line = self.screen.pop(self.scrollRegion[1])
            for i in range(self.cols):
                line[i] = u' '
            self.screen.insert(self.curY+l, line)
            self.isLineDirty[self.curY+l] = True
            rendition = self.scrRendition.pop(self.scrollRegion[1])
            for i in range(self.cols):
                rendition[i] = 0
            self.scrRendition.insert(self.curY+l, rendition)
        return
    def __OnEscSeqDL(self, params, end):
        """
        Handler for escape sequence DL
        """
        self.curX = 0
        n = int(params) if params != None else 1
        for l in range(n):
            self.isLineDirty[self.curY+l] = True
            line = self.screen.pop(self.curY+l)
            for i in range(self.cols):
                line[i] = u' '
            self.screen.insert(self.scrollRegion[1], line)
            self.isLineDirty[self.scrollRegion[1]] = True
            rendition = self.scrRendition.pop(self.curY+l)
            for i in range(self.cols):
                rendition[i] = 0
            self.scrRendition.insert(self.scrollRegion[1], rendition)
        return
    def __OnEscSeqDCH(self, params, end):
        """
        Handler for escape sequence DCH
        """
        n = int(params) if params != None else 1
        self.isLineDirty[self.curY] = True
        for c in range(self.curX,self.cols):
            if c + n < self.cols:
                self.screen[self.curY][c] = self.screen[self.curY][c+n]
                self.scrRendition[self.curY][c] = self.scrRendition[self.curY][c+n]
            else:
                self.screen[self.curY][c] = ' '
                self.scrRendition[self.curY][c] = 0
        return
    def __OnEscSeqVPA(self, params, end):
        """
        Handler for escape sequence VPA
        """
        if params == None:
            glsLog.debug("TE WARNING: VPA without parameter", 2)
            return
        row = int(params)
        # convert it to zero based index
        row -= 1
        if row >= 0 and row < self.rows:
            self.curY = row
        else:
            glsLog.debug("TE WARNING: VPA line no. out of boundary", 2)
        return
    def __OnEscSeqSGR(self, params, end):
        """
        Handler for escape sequence SGR
        """
        if params != None:
            renditions = params.split(';')
            for rendition in renditions:
                irendition = int(rendition)
                if irendition == 0:
                    # reset rendition
                    self.curRendition = 0
                elif irendition > 0 and irendition < 9:
                    # style
                    self.curRendition |= (1 << (irendition - 1))
                elif irendition >= 30 and irendition <= 37:
                    # foreground
                    self.curRendition |= ((irendition - 29) << 8) & 0x00000f00
                elif irendition >= 40 and irendition <= 47:
                    # background
                    self.curRendition |= ((irendition - 39) << 12) & 0x0000f000
                elif irendition == 27:
                    # reverse video off
                    self.curRendition &= 0xffffffbf
                elif irendition == 39:
                    # set underscore off, set default foreground color
                    self.curRendition &= 0xfffff0ff
                elif irendition == 49:
                    # set default background color
                    self.curRendition &= 0xffff0fff
                else:
                    glsLog.debug("TE WARNING: Unsupported rendition %s"%irendition, 2)
                    pass
        else:
            # reset rendition
            self.curRendition = 0
        return
    def __OnEscSeqSETCLRM(self, params, end):
        """
        Handler for escape sequence SETM / CLRM.
        Calls the mode change callback with the dictionary of modes.
        """
        if params == None:
            glsLog.debug("TE WARNING: SETM / CLRM without parameter", 2)
            return
        if params not in self.modes:
            glsLog.debug("TE WARNING: Unknown mode: '%s%s'"%(params,end), 2)
            return
        if end == 'h':
            self.modes[params] = True
        elif end == 'l':
            self.modes[params] = False
        if self.callbacks[self.CALLBACK_MODE_CHANGE] != None:
            self.callbacks[self.CALLBACK_MODE_CHANGE](self.modes)
        return
    def __OnEscSeqCSR(self, params, end):
        """
        Handler for escape sequence CSR.
        """
        if params == None:
            glsLog.debug("TE WARNING: CSR without parameter", 2)
            return
        args = params.split(';')
        if len(args) != 2:
            __UnhandledEscSeq(params+end)
            return
        row_start, row_end = args
        row_start = int(row_start) - 1
        row_end   = int(row_end)   - 1
        row_start = row_start if row_start > 0         else 0
        row_end   = row_end   if row_end   < self.cols else self.cols-1
        self.scrollRegion = (row_start, row_end)
        self.curX = 0
        self.curY = 0
        return
    def __OnEscSeqCSZ(self, params, end):
        """
        Handler for escape sequence CSZ.
        """
        if params == None:
            glsLog.debug("TE WARNING: CSZ without parameter", 2)
            return
        if len(params) != 2 or params[0] != '?':
            __UnhandledEscSeq(params+end)
            return
        style = int(params[1])
        if style not in (0, 1, 2, 8):
            style = self.CURSOR_STYLE_DEFAULT
        if style != self.cursorStyle:
            self.cursorStyle = style
            if self.callbacks[self.CALLBACK_CURSOR_CHANGE] != None:
                self.callbacks[self.CALLBACK_CURSOR_CHANGE](self.cursorStyle)
        return
