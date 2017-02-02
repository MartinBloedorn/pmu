from pmu_workspace import *
from pmu_buffers import *

from collections import OrderedDict
from typing import Union

import sys
import csv
import re
import os
import os.path


class GenericParser(object):
    def __init__(self, bufferType=GenericBuffer):
        self.__filepath = None
        self.__buff     = bufferType()
        self.__verbose  = False

    @property
    def filepath(self):
        return self.__filepath

    @filepath.setter
    def filepath(self, value):
        if type(value) is not str:
            raise TypeError("Path to file must be a string.")
        self.__filepath = value

    @property
    def buffer(self):
        return self.__buff

    @buffer.setter
    def buffer(self, value):
        if type(value) is not type (self.__buff):
            raise TypeError
        self.__buff = value

    @property
    def verbose(self):
        return self.__verbose

    @verbose.setter
    def verbose(self, value):
        if type(value)is not bool:
            raise TypeError
        self.__verbose = value

    def parse_file(self, fpath=None) -> bool:
        self.__filepath = fpath if fpath is not None else self.__filepath
        if self.__filepath is None:
            return False
        if not os.path.isfile(self.__filepath):
            print('{} does not exist!'.format(self.__filepath))
            return False
        # Clear buffer
        self.__buff.clear()
        # Parsing done in derived classes
        return True


class ConfParser(GenericParser, DefaultWorkspace):
    """
    Parses/writes PMU configuration files.
    After parsing, holds the parameter dictionary.
    """

    def __init__(self):
        GenericParser.__init__(self)
        DefaultWorkspace.__init__(self)

    def parse_file(self, fpath=None) -> bool:
        if not super().parse_file(fpath):
            return False

        cfd = open(self.filepath, 'r')
        print('Parsing configuration file {}'.format(self.filepath))

        __indict = OrderedDict()
        for line in cfd:
            # Is a comment
            if re.match('[\s\t]*#.*', line) is not None:
                continue
            # Is an entry; expand any pre-existing variables
            try:
                line = self.__expand_variables(line, __indict)
            except:
                continue
            m = re.match('[\s\t]*(?P<varname>\S*)[\s\t]*=[\s\t]*(?P<varcontent>\S*)[\s\t]*(#.*)?', line)
            m = re.match('[\s\t]*(?P<varname>\S*)[\s\t]*=[\s\t]*(?P<varcontent>[^#^\n]*)', line)
            if m is not None and m.group('varname') and m.group('varcontent'):
                __indict[m.group('varname')] = m.group('varcontent')
                continue
        # print(self.paramdict)
        self.parse_dict(__indict, allow_new=True)
        cfd.close()

    def set(self, name, value):
        """
        Changes or adds an entry in/to the paramdict.
        """
        if type(name) is str:
            if name not in self.param:
                print('Adding new variable {} to workspace.'.format(name))
            try:
                # self[name] = self.__expand_variables(value)
                self.parse_dict({name: self.__expand_variables(value)}, allow_new=True)
            except:
                pass

    def get(self, name) -> Union[str, None]:
        if name not in self.param:
            print('No variable {} in workspace!'.format(name))
            return None
        return self[name]

    def delete(self, name):
        """
        Removes entry from paramdict:
        """
        if type(name) is str:
            if name in self.param:
                del self[name]
            else:
                print('No variable {} to delete.'.format(name))

    def __expand_variables(self, line, dict=None) -> str:
        dict = self.dict if dict is None else dict
        m = []
        while m is not None:
            m = re.match('(.*)\$\((?P<varname>\w*)\)(.*)', line)
            if m is not None:
                if m.group('varname') not in dict:
                    print('Undefined variable {}'.format(m.group('varname')))
                    raise Exception
                line = m.group(1) + dict[m.group('varname')] + m.group(3)
        return line


class HMapParser(GenericParser):
    """
    Reads/parses heightmap CSV files.
    """

    def __init__(self):
        GenericParser.__init__(self, HMapBuffer)

    def parse_file(self, fpath=None) -> bool:
        if not super().parse_file(fpath):
            return False

        print('Parsing heigthmap file {}'.format(self.filepath))
        with open(self.filepath, 'r') as hfd:
            line = csv.reader(hfd, delimiter=',')
            for row in line:
                try:
                    x = float(row[0])
                    y = float(row[1])
                    z = float(row[2])
                except:
                    print('Unable to parse heightmap.')
                    return False
                self.buffer.append((x, y, z))
        return True

    def write_file(self, fpath=None):
        pass


class GCodeParser(GenericParser):
    """
    Reads/parses and writes GCode.
    All values are converted to and handled in mm.
    """
    def __init__(self):
        GenericParser.__init__(self, GCodeBuffer)

    def parse_file(self, fpath = None) -> bool:
        if not super().parse_file(fpath):
            return False

        gfd = open(self.filepath, 'r')
        print('Parsing GCode file {}'.format(self.filepath))

        lineno = 0
        gcmdno = 0
        for line in gfd:
            lineno += 1
            # Is line a G00 or G01?
            x, y, z, f, g = [None for _ in range(5)]
            for m in re.finditer('.*G(?P<g>[0-9\.]*)|.*F(?P<f>[0-9\.]*)|.*X(?P<x>[0-9\.-]*)|'
                                 '.*Y(?P<y>[0-9\.-]*)|.*Z(?P<z>[0-9\.-]*)', line):
                try:
                    x = float(m.group('x')) if m.group('x') is not None else x
                    y = float(m.group('y')) if m.group('y') is not None else y
                    z = float(m.group('z')) if m.group('z') is not None else z
                    f = float(m.group('f')) if m.group('f') is not None else f
                    g = int(m.group('g'))   if m.group('g') is not None else g
                except:
                    print('In GCode file: unable to processes line {}'.format(line))
                    return False
            # Currently accept only G01 and G00 as motion codes
            if any([i is not None for i in [x, y, z, f, g]]) and g in [0,1]:
                self.buffer.append((g, f, x, y, z))
                gcmdno += 1
            # Line was not recognized as a G command; archive it entirely
            else:
                self.buffer.append(line)
                if self.verbose:
                    print('Line {} - not a G command: {}'.format(lineno, line.replace('\n','').replace('\r','')))

        gfd.close()
        print('Parsed {} lines, with {} valid G commands'.format(lineno, gcmdno))
        return True

    def write_file(self, fpath, buffer=None) -> bool:
        if fpath is None or fpath.strip() is '':
            return False
        if type(buffer) is not GCodeBuffer:
            print('GCodeParser: wrong buffer type.')
            return False
        try:
            ofd = open(fpath, 'w')
        except:
            print('GCodeParser: {}'.format(sys.exc_info()[1]))
            return False
        if buffer is None:
            buffer = self.buffer

        for bl in buffer:
            #print(bl)
            if not GCodeBuffer.is_motion(bl):
                ofd.write('{}'.format(bl))
                continue
            line = str()
            g = GCodeBuffer.get_gc(bl)
            f = GCodeBuffer.get_fr(bl)
            p = GCodeBuffer.get_pt(bl)
            if g is not None:
                line += 'G0{} '.format(g)
            if f is not None:
                line += 'F{} '.format(f)
            for i, a in enumerate(['X','Y','Z']):
                line += ' {}{}'.format(a, p[i]) if p[i] is not None else ''
            ofd.write('{}\n'.format(line))
        ofd.close()
        return True


class ExcellonParser(GenericParser):
    """
    Reads/parses Excellon drill files.
    All values are converted to and handled in mm.
    """
    def __init__(self):
        GenericParser.__init__(self, ExcellonBuffer)

        self.__excellonFormat = None
        self.__excellonZeroT  = None

        # Dictionary indexed by toolname; tuple with diameter/drill list (list of X/Y tuples).
        # All units are metric
        self.__drill = OrderedDict()
        self.__drill['T0'] = (-1, []) # Default tool; may be empty (diam = -1)
        self.__currdrill   = None

    def parse_file(self, fpath = None) -> bool:
        if not super().parse_file(fpath):
            return False

        efd = open(self.filepath, 'r')
        print('Parsing drill file {}'.format(self.filepath))

        for line in efd:
            # Is line a comment?
            if re.match('[\s\t]*;.*', line) is not None:
                continue
            # If file uses incremental (ICI) mode, break; unsupported
            if re.match('[\s\t]*ICI', line) is not None:
                print('Excellon file uses unsupported incremental mode (ICI).')
                return False
            # Is line a format definition?
            m = re.match('[\s\t]*(?P<format>\w*),(?P<zerot>\w*)', line)
            if m is not None and m.group('format') and m.group('zerot'):
                self.__excellonFormat = m.group('format').upper()
                self.__excellonZeroT  = m.group('zerot').upper()
            # Is line a tool definition?
            m = re.match('[\s\t]*(?P<id>T[0-9]*)C(?P<diam>[0-9\.]*)', line)
            if m is not None and m.group('id') and m.group('diam'):
                try:
                    diam = float(m.group('diam'))
                except:
                    print('In excellon file: incorrect definition for {}'.format(m.group('id')))
                    return False
                self.__drill[m.group('id')] = (diam, [])
            # Is line beginnig a tool group?
            m = re.match('[\s\t]*(?P<id>T[0-9]*)[^.]*', line)
            if m is not None and m.group('id'):
                id = m.group('id')
                if id not in self.__drill:
                    print('In excellon file: undefined tool {}'.format(id))
                    return False
                self.__currdrill = id
            # Is line a drill definition?
            m = re.match('.*X(?P<x>[0-9\.]*)Y(?P<y>[0-9\.]*)', line)
            if m is not None and m.group('x') and m.group('y') and self.__currdrill is not None:
                try:
                    x = self.__convert_unit(float(m.group('x')))
                    y = self.__convert_unit(float(m.group('y')))
                except:
                    print('In excellon file: unable to parse drill - {}'.format(m.group(0)))
                    return False
                self.__drill[self.__currdrill][1].append((x, y))
        efd.close()
        # Translate dictionary into system-wide usable buffer
        self.__gen_drill_buffer()
        return True

    def __gen_drill_buffer(self):
        """
        Returns self.drill organized into a list of tuples:
        (diam, x, y)
        """
        self.buffer.clear()
        for t in self.__drill:
            for d in self.__drill[t][1]:
                self.buffer.append([self.__drill[t][0], d[0], d[1]])

    def __convert_unit(self, value) -> float:
        """
        Converts and returns the input value into an absolute metric value.
        All units are in mm.

        \TODO: Support LT and TZ schemes, investigate further formats.
        """
        if self.__excellonFormat is None or self.__excellonZeroT is None:
            print('Incorrect format definition for excellon file.')
            raise Exception
        if self.__excellonFormat == 'METRIC':
            return value
        elif self.__excellonFormat == 'INCH':
            return value * 25.4