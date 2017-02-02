from collections import OrderedDict
from enum import Enum
from pmu_buffers import *

import re
import sys
import os


class Const(object):
    def __setattr__(self, key, value):
        if key in self.__dict__:
            raise AttributeError('Can\'t rebind.')
        else:
            self.__dict__[key] = value
    def __init__(self):
        pass
    def __str__(self):
        return str(self.__dict__)


class DefaultParamNameTable():
    """
    Singleton class for parameter name abstraction table.
    """
    __instance = None
    class __DefaultParamNameTable(Const):
        def __init__(self):
            Const.__init__(self)
            # Variable name bindings
            self.precision    = 'precision'

            self.drltol       = 'drltol'
            self.drlscope     = 'drlscope'
            self.drlstep      = 'drlstep'
            self.maxiter      = 'maxiter'
            self.randiter     = 'randiter'
            self.probe_lims   = 'probe_lims'
            self.probe_tick   = 'probe_tick'
            self.mirrorax     = 'mirrorax'
            self.mirrorval    = 'mirrorval'

            self.mincutdepth  = 'mincutdepth'
            self.initialcoord = 'initialcoord'
            self.zthreshold   = 'zthreshold'
            self.xysampling   = 'xysampling'

    def __init__(self):
        if not DefaultParamNameTable.__instance:
            DefaultParamNameTable.__instance = DefaultParamNameTable.__DefaultParamNameTable()
    def __getattr__(self, item):
        return getattr(self.__instance, item)
    def __setattr__(self, key, value):
        return setattr(self.__instance, key, value)
    def __str__(self):
        return str(self.__instance)


class BaseWorkspace(object):
    """
    Specifies a dictionary that can only receive pre-defined types of variables.
    Lists also have pre-defined types of accepted variables.
    """
    def __init__(self, groupname=''):
        self.__paramdict = OrderedDict()
        self.__groupname = groupname # Defaults to '', root (free) group
        self.__pt        = DefaultParamNameTable()

    @property
    def param(self) -> dict:
        return self.__paramdict

    @property
    def paramgroup(self) -> str:
        """ Returns the name under which the parameters are grouped. """
        return self.__groupname

    @property
    def pt(self):
        return self.__pt

    def __tl(self, key) -> list:
        """ Return type list. """
        return self.__paramdict[key][0]

    def __delitem__(self, key):
        if key in self.__paramdict:
            del self.__paramdict[key]

    def __getitem__(self, item):
        try:
            return self.__paramdict[item][1]
        except:
            return None

    def __setitem__(self, key, value) -> bool:
        """ Will set the paramdict[key] to the accepted type (or list of accepted types)."""
        if key not in self.__paramdict or type(value) not in self.__tl(key):
            return False
        if type(value) is list and \
                not all([j in self.__tl(key) for j in [type(i) for i in value]]):
            return False
        self.__paramdict[key][1] = value
        return True

    def addparam(self, key: str, typ: list, val):
        """ Add a parameter with predefined key and type.
        If is list, define at least one element type, e.g., addparam('l', [list,int], [1,2])"""
        if type(key) is not str or type(typ) is not list:
            raise TypeError
        if typ[0] is list and len(typ) < 2:
            raise ValueError
        self.__paramdict[key] = [typ, val]

    def parse_dict(self, dict):
        """Parses dictionary. Converts variables to registered types, including lists."""
        for key in dict:
            if key not in self.__paramdict:
                continue
            if type(dict[key]) is str and self.type(key) is list:
                self[key] = [self.__tl(key)[1](i) for i in \
                     dict[key].replace('[','').replace(']','').split(',')]
            else:
                self[key] = self.type(key)(dict[key])

    def type(self, key):
        try:
            return self.__paramdict[key][0][0]
        except:
            return type(None)

