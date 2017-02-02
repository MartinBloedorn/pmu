from collections import OrderedDict
from enum import Enum
from typing import Union

import re
import sys
import os


class BuffType(Enum):
    NONE, GRID, HMAP, GCOD, EXCE = range(5)


class GenericBuffer(object):
    def __init__(self, type = BuffType.NONE):
        self.__data   = list()
        self.__type   = type
        self.__size   = 0
        self.__i      = 0

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, value):
        if type(value) is not list:
            raise TypeError
        self.__data = value
        self.__size   = len(value)

    @property
    def type(self):
        return self.__type

    @property
    def size(self):
        return self.__size

    def __str__(self):
        return "<" + self.__type.name + ": " + str(self.__size) + ">"

    def __iter__(self):
        self.__i = 0
        return self

    def __next__(self):
        if self.__i < self.__size:
            self.__i += 1
            return self.__data[self.__i - 1]
        else:
            raise StopIteration

    def current(self):
        return self.__data[self.__i]

    def append(self, value):
        self.__data.append(value)
        self.__size = len(self.__data)

    def clear(self):
        self.__data.clear()
        self.__size = 0

    def empty(self) -> bool:
        return self.__size == 0


class GridBuffer(GenericBuffer):
    def __init__(self):
        GenericBuffer.__init__(self, BuffType.GRID)


class GCodeBuffer(GenericBuffer):
    def __init__(self):
        GenericBuffer.__init__(self, BuffType.GCOD)

    @staticmethod
    def is_motion(bl) -> bool:
        return type(bl) is tuple and len(bl) == 5 and \
               all([isinstance(i,(int,float,type(None))) for i in bl])

    @staticmethod
    def get_motion_params(bl) -> Union[dict, None]:
        if not GCodeBuffer.is_motion(bl):
            return None
        return {'g': bl[0], 'f': bl[1], 'x': bl[2], 'y': bl[3], 'z': bl[4]}

    @staticmethod
    def get_gc(bl): return bl[0]

    @staticmethod
    def get_fr(bl): return bl[1]

    @staticmethod
    def get_pt(bl): return [bl[2], bl[3], bl[4]]


class HMapBuffer(GenericBuffer):
    def __init__(self):
        GenericBuffer.__init__(self, BuffType.HMAP)


class ExcellonBuffer(GenericBuffer):
    def __init__(self):
        GenericBuffer.__init__(self, BuffType.EXCE)

