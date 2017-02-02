from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import matplotlib.pyplot as plt

from pmu_workspace import *
from pmu_parsers import *
from pmu_buffers import *

class pmuView(DefaultWorkspace):
    def __init__(self):
        DefaultWorkspace.__init__(self)
        self.__gcf  = None # Current figure
        self.__gca  = None # Current axis
        self.__grid = False
        self.__scl  = 1.1
        plt.ion()

    def __gcaf(self):
        if self.__gca is None or self.__gcf is None:
            self.new_window()
        else:
            self.__gca = plt.gca()
            self.__gcf = plt.gcf()

    def __scale(self, lin: list, factor: float) -> list:
        """ Scale [start, end] by a factor."""
        d = abs(lin[1] - lin[0])
        return [min(lin)-(d*(factor-1.0)), max(lin)+(d*(factor-1.0))]

    def __setup_plot(self):
        self.__gcaf()
        self.__gca.set_xlim(self.__scale(self[self.pt.probe_lims][0:2], self.__scl))
        self.__gca.set_ylim(self.__scale(self[self.pt.probe_lims][2:4], self.__scl))
        self.__gca.set_aspect('equal')

    def toggle_grid(self):
        self.__grid = not self.__grid
        self.__gcaf()
        plt.grid(self.__grid)
        plt.draw()

    def new_window(self):
        self.__gcf, self.__gca = plt.subplots()

    def clear_plot(self):
        self.__gca = plt.gca()
        self.__gca.cla()
        self.__grid = False

    def print_drills(self, drills: ExcellonBuffer, print_tol=False):
        if drills is None:
            print('View: empty drill buffer.')
            return

        self.__setup_plot()
        # [diam, x, y]
        for d in drills:
            c = plt.Circle((d[1],d[2]), d[0]/2.0, color='r', fill=False)
            self.__gca.add_artist(c)
            if print_tol:
                c = plt.Circle((d[1], d[2]), (d[0]/2.0 + self[self.pt.drltol]), color='y', fill=False)
                self.__gca.add_artist(c)
        plt.grid(self.__grid)
        plt.draw()

    def print_probe(self, grid: GridBuffer):
        if type(grid) is not GridBuffer:
            print('View: wrong buffer type.')
            return
        if grid is None:
            print('View: empty buffer.')
            return

        self.__setup_plot()
        # [x, y]
        for g in grid:
            self.__gca.plot(g[0], g[1], 'x', color='blue')
        plt.grid(self.__grid)
        plt.draw()