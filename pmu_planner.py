from collections import OrderedDict
from enum import Enum

from pmu_workspace import *

import scipy as sp
from scipy import interpolate
from scipy.spatial.distance import pdist

import re
import sys
import os


class pmuPlanner:
    """
    Implements handling of main functions (leveling, cropping, redo, painting...).
    Holds references to active files (gcode, drill, hmap) and output gcode buffer.
    """
    def __init__(self):
        self.activeGCodeFile = None
        self.activeDrillFile = None
        self.activeHMapFile  = None

        self.__buff     = GenericBuffer()
        self.__buffDesc = ''

        self.__Leveler  = Leveling()

    @property
    def buffer(self):
        return self.__buff

    @property
    def bufferType(self) -> str:
        return self.__buff.type.name

    @property
    def bufferDescription(self) -> str:
        return self.__buffDesc

    @property
    def Leveler(self):
        return self.__Leveler

    def leveling_set_params(self, probLims, probTick):
        try: self.__Leveler.set_probing_params(probLims, probTick)
        except: print('Planner: wrong probing parameters.')

    def leveling_gen_grid(self, drills=None, mirrpos=None, mirrax=None) -> bool:
        try: r = self.__Leveler.gen_probing_grid(drills, mirrpos, mirrax)
        except:
            print('Planner: {}'.format(sys.exc_info()[1]))
            return False
        if r:
            self.__buff     = self.__Leveler.probingGrid
            self.__buffDesc = '{} probing points'.format(self.__buff.size)
        return r

    def leveling_run(self, gcodebuff: GCodeBuffer, hmapbuff: HMapBuffer) -> bool:
        if gcodebuff.empty():
            print('Planner: no active GCode has been loaded yet.')
            return False
        try: r = self.__Leveler.run_leveling(gcodebuff, hmapbuff)
        except:
            print('Planner: {}'.format(sys.exc_info()[1]))
            return False
        if r:
            self.__buff     = self.__Leveler.leveledGCode
            self.__buffDesc = 'Leveled GCode, {} lines'.format(self.__buff.size)
        return r


class Leveling(DefaultWorkspace):
    """
    Explanation.
    """
    def __init__(self):
        DefaultWorkspace.__init__(self)

        self.__probingGrid  = GridBuffer()
        self.__lvlGCodeBuff = GCodeBuffer() # Leveled GCode buffer

        self.__verbose = True
        self.__surff   = None

    @property
    def probingGrid(self):
        return self.__probingGrid

    @property
    def leveledGCode(self) -> GCodeBuffer:
        return self.__lvlGCodeBuff

    def set_probing_params(self, probLims, probTick):
        """
        [float(i) for i in "[1 2 3]".replace('[','').replace(']','').strip().split(' ')]
        :param probLims: [xmin xmax ymin ymax]
        :param probTick: [pts_in_x pts_in_y]
        """
        if type(probLims) is not list or type(probTick) is not list:
            raise TypeError
        if len(probLims) != 4 or probLims[0] >= probLims[1] or probLims[2] >= probLims[3]:
            raise ValueError
        self[self.pt.probe_lims] = [float(i) for i in probLims]
        self[self.pt.probe_tick] = [int(i)   for i in probTick]

    def gen_probing_grid(self, drills=None, mirrpos=None, mirrax=None) -> bool:
        """
        Generates coordinates for probing points.
        Updates self.__probingGrid
        :param drills: List of excellon drills: [diam x y]. If None, ignored.
        :param mirrpos: Position of mirroring axis.
        :param mirrax:  Mirror axis parallel to ('x', 'y' or 0, 1)
        :return: True if probing points were correctly generated.
        """
        if drills is not None and type(drills) is not ExcellonBuffer:
            raise TypeError
        if mirrpos is not None and type(mirrpos) is not float:
            raise TypeError
        if mirrax is not None and mirrax not in ['x', 'y', 0, 1]:
            raise ValueError

        # Copy input list
        __drills = list(drills) if drills is not None else []
        self.__probingGrid.clear()

        # Mirroring drills if necessary
        if drills and self[self.pt.mirrorax] in ['x', 'y']:
            print('Leveler: mirroring drills parallel to {}, at {}'.format(
                self[self.pt.mirrorax], self[self.pt.mirrorval]))
            i = 1 if self[self.pt.mirrorax] is 'x' else 2
            for d in __drills:
                d[i] += 2*(self[self.pt.mirrorval] - d[i])

        probl = self[self.pt.probe_lims]
        probt = self[self.pt.probe_tick]
        # Compute grid itself,
        for xp in sp.linspace(probl[0], probl[1], probt[0]):
            for yp in sp.linspace(probl[2], probl[3], probt[1]):
                p = sp.array([xp, yp])

                collision = False
                drl2avoid = []
                niter     = 0
                for d in __drills:
                    dist = pdist([p,d[1:3]])[0] # d = [diam x y]
                    collision |= (dist - d[0]/2) < self[self.pt.drltol]
                    if dist < self[self.pt.drlscope]:
                        drl2avoid.append(d)

                # If a collison is happening, move probing pt
                while collision and niter < self[self.pt.maxiter]:
                    sp.random.seed()
                    niter += 1
                    d2p = [] # Vectors from drills to p
                    for d in drl2avoid:
                        v = sp.subtract(p,d[1:3])
                        v = v/(sp.linalg.norm(2)**2)
                        d2p.append(v)
                    resultVec = sp.sum(d2p, axis=0)
                    resultVec = self[self.pt.drlstep]*(resultVec/sp.linalg.norm(resultVec))
                    # Apply fixed step to point
                    p = sp.sum([p, resultVec], axis=0)
                    # Verify if collison if resolved
                    collision = any([pdist([p,d[1:3]])[0] - d[0]/2 < self[self.pt.drltol] for d in drl2avoid])

                    if not collision and self.__verbose:
                        print('Avoided drill by moving probe to {}'.format(p.round(4)))
                    # Not converging. Add some random motion.
                    if niter > self[self.pt.randiter]:
                        randVec = self[self.pt.drlstep]*sp.array([sp.rand()-.5, sp.rand()-.5])
                        p = sp.sum([p, randVec], axis=0)

                if collision:
                    return False

                # Append point to generated grid
                self.__probingGrid.append(p.round(self[self.pt.precision]).tolist())
        return True

    def run_leveling(self, gcodebuff: GCodeBuffer, hmapbuff: HMapBuffer):
        """
        :param gcodebuff: List of string or (g, f, [x,y,z]) fields
        :param hmapbuff:  List of (x,y,z) tuples
        :return: None
        """
        # print('Types = {} {} '.format(type(gcodebuff), type(hmapbuff)))
        if type(gcodebuff) != GCodeBuffer or type(hmapbuff) != HMapBuffer:
            raise TypeError
        if hmapbuff.size < 4:
            raise ValueError('Heightmap must have more than 4 entries.')
        # Empty existing output buffer
        self.__lvlGCodeBuff.clear()
        cur_coord = self[self.pt.initialcoord]

        # Creating surface function from heightmap
        x, y, z = [list() for _ in range(3)]
        for p in hmapbuff:
            x.append(p[0])
            y.append(p[1])
            z.append(p[2])
        _kind = 'cubic' if hmapbuff.size >= 16 else 'linear'
        surff = interpolate.interp2d(x, y, z, kind=_kind)
        newpts = 0

        # Apply leveling
        for line in gcodebuff:
            # Throughput non-motion lines
            if not GCodeBuffer.is_motion(line):
                self.__lvlGCodeBuff.append(line)
                continue

            # \TODO: GCodeBuffer checks for G00 and G01 cmds. Ideally, this should happen here.
            # Fetching new coordinates and pulling unchanged values from previous coordinate
            new_coord = GCodeBuffer.get_pt(line)
            for i in range(0,3):
                new_coord[i] = cur_coord[i] if new_coord[i] is None else new_coord[i]
            ep = self.__expand_points(cur_coord, new_coord, surff)
            newpts += len(ep) - 1
            for p in ep:
                self.__lvlGCodeBuff.append((GCodeBuffer.get_gc(line), GCodeBuffer.get_fr(line),
                                            p[0], p[1], p[2]))
            cur_coord = new_coord
        print('Leveler: added {} intermediary points to leveled GCode'.format(newpts))
        return True

    def __expand_points(self, p0, p1, surff) -> list:
        """
        ASCII drawing to come.
        """
        rl = list() # return list
        p0 = sp.array(p0)
        p1 = sp.array(p1)
        dist = sp.linalg.norm(p1[0:2] - p0[0:2]) # 2d distance only
        # wont append starting point; is endpoint of previous segment;
        # automatically avoids printing start coordinate to outupt
        cz = surff(p0[0], p0[1])  # start point depth correction
        # number of tick points to inspect
        n = int(sp.ceil(dist/self[self.pt.xysampling]))
        if n > 1:
            # tick between start and end points
            xt = sp.linspace(p0[0], p1[0], n, False)
            yt = sp.linspace(p0[1], p1[1], n, False)
            for i in range(1,n): # don't iterate over start/endpoints
                zi = surff(xt[i], yt[i]) # if new depth correction is too large,
                if abs(zi - cz) > self[self.pt.zthreshold]:
                    cz = zi
                    di = sp.linalg.norm(sp.array((xt[i], yt[i])) - p0[0:2])
                    z01= p0[2] + (p1[2]-p0[2])*(di/dist) # interpolate original depth
                    rl.append([float(sp.round_(i, self[self.pt.precision])) for i in [xt[i], yt[i], z01 + cz]])
        # append end point
        cz = surff(p1[0], p1[1])  # start point depth correction
        rl.append([float(sp.round_(i, self[self.pt.precision])) for i in [p1[0], p1[1], p1[2] + cz]])
        return rl