import re
import sys
import random

from collections import OrderedDict
from pmu_planner   import *
from pmu_view      import *

class pmuCLI:
    """
    Simple command-line interface for PMU.
    """
    def __init__(self):
        self.descriptionText = ''
        self.versionString = ''
        self.confFilePath = ''
        self.cmd = []
        self.arg = []

        self.greetingText = ('\nWelcome to the PMU shell.\n'
                             'Enter `help` for a list of available commands or `quit` to leave.\n')

        # Commands are a dict indexed by the command name.
        # Each entry contains the function, description and detailed description
        self.commands    = OrderedDict()

        self.register_command(self.print_help,   'help', 'Show this help.',
                                                 'That\'s helpless.')
        self.register_command(self.exit, 'quit', 'Leave PMU.', '')
        self.register_command(self.list, 'list', 'List variables in workspace.',
                                                 "Usage: list [work|drl|grid]")
        self.register_command(self.set_variable, 'set', 'Set variable in workspace.',
                                                 "Usage: set <varname> <value>", 2)
        self.register_command(self.del_variable, 'del', 'Remove variable from workspace.', "Usage: del <varname>", 1)
        self.register_command(self.load,         'load', 'Load and parse external files.',
                                                 "Usage: load [drl|hmap|fcu|bcu]\n"
                                                 "       load gcode <varname>", 1)
        self.register_command(self.unload, 'unload', 'Unload selected active file.',
                                                 "Usage: load [drl|hmap|fcu|bcu|gcode]", 1)
        self.register_command(self.write,  'write',  'Write work buffer to file.',
                                                 "Usage: write <varname>", 1)
        self.register_command(self.level,  'level',  'Apply leveling to GCode.',
                                                 "Usage: level [file|buffer]")
        self.register_command(self.probe,  'probe', 'Generate grid and execute probing.',
                                                 "Usage: probe [grid]\tGenerate grid.\n"
                                                 "       probe run   \tConnect to CNC and execute probing.")
        self.register_command(self.view,   'view', 'Visualize data.',
                                                 "Usage: view [drl|probe|new|clear|grid]", 1)

        # PMU Model objects
        self.pmuConfParser  = ConfParser()
        self.excellonParser = ExcellonParser()
        self.hmapParser     = HMapParser()
        self.Planner        = pmuPlanner()
        self.gcodeParser    = GCodeParser()
        self.View           = pmuView()

    def run(self):
        # Parse project configuration; exits on error
        self.pmuConfParser.parse_file(self.confFilePath)
        # If excellon file was declared, try to parse it:
        self.load(['drl'])
        # If heightmap file was declared, try to parse it:
        self.load(['hmap'])
        # If frontcopper was declared, try to load it:
        self.load(['fcu'])

        print(self.greetingText)

        while True:
            liin = input('pmu> ')
            argv = liin.strip().split(' ')
            # argv = re.findall(r"[\w']+", liin)
            argc = len(argv) - 1 # exclude command itself

            self.cmd = argv[0]
            self.arg = argv[1:] if argc > 0 else []

            if self.cmd is not '':
                if self.cmd not in self.commands:
                    print('Unrecognized command {}'.format(self.cmd))
                    continue
                # Executing commands from registered command list
                if argc >= self.commands[self.cmd]['minc']:
                    self.commands[self.cmd]['f'](self.arg)
                else:
                    self.print_help([self.cmd])

    def set_variable(self, arglist):
        self.pmuConfParser.set(arglist[0], ' '.join(arglist[1:]))

    def del_variable(self, arglist):
        self.pmuConfParser.delete(arglist[0])

    def load(self, arglist):
        # load command 'aliases'
        if len(arglist) == 1:
            if   arglist[0] == 'drl':
                self.load(['drl',   'excellon_path'])
            elif arglist[0] == 'hmap':
                self.load(['hmap',  'hmap_path'])
            elif arglist[0] == 'fcu':
                self.load(['gcode', 'fcu_path'])
            else:
                self.print_help(['load'])
        # processing type and variable
        elif len(arglist) == 2:
            var = self.pmuConfParser.get(arglist[1])
            if var is None:
                return
            if   arglist[0] == 'gcode':
                if self.gcodeParser.parse_file(var):
                    self.Planner.activeGCodeFile = var
            elif arglist[0] == 'drl':
                if self.excellonParser.parse_file(var):
                    self.Planner.activeDrillFile = var
            elif arglist[0] == 'hmap':
                if self.hmapParser.parse_file(var):
                    self.Planner.activeHMapFile = var
            else:
                self.print_help(['load'])
        else:
            self.print_help(['load'])

    def unload(self, arglist):
        if arglist[0] == 'drl':
            self.Planner.activeDrillFile = None
            self.excellonParser.buffer.clear()
        elif arglist[0] == 'hmap':
            self.Planner.activeHMapFile  = None
            self.hmapParser.buffer.clear()
        elif arglist[0] in ['fcu', 'bcu', 'gcode']:
            self.Planner.activeGCodeFile = None
            self.gcodeParser.buffer.clear()
        else:
            self.print_help(['unload'])

    def write(self, arglist):
        var = self.pmuConfParser.get(arglist[0])
        if self.Planner.buffer.size == 0:
            print('Won\'t write an empty buffer.')
            return
        if var is not None:
            if type(self.Planner.buffer) is GCodeBuffer:
                if self.gcodeParser.write_file(var, self.Planner.buffer):
                    print('Successfully wrote to file {}'.format(var))
                else:
                    print('Failed to write to {}'.format(var))
            else:
                print('Work buffer type can not be saved.')

    def list(self, arglist):
        # List the workspace variables
        if len(arglist) == 0 or arglist[0] == 'work':
            print('\n\t:Workspace:')
            for v in self.pmuConfParser.param:
                print('{}'.format(v) + ' ' * (20 - len(v)) + '\t=  {}'.format(self.pmuConfParser[v]))
            print('\n\t:Active files:')
            print('GCode          : {}'.format(self.Planner.activeGCodeFile))
            print('Excellon       : {}'.format(self.Planner.activeDrillFile))
            print('Heightmap      : {}'.format(self.Planner.activeHMapFile))
            print('\nWork Buffer    : {} ({})'.format(self.Planner.buffer, self.Planner.bufferDescription))
        # List the parsed drill points
        elif arglist[0] == 'drl':
            print('\n\t:Drills:\nDiam\tX   \tY')
            for d in self.excellonParser.buffer:
                print('{}\t{}\t{}'.format(d[0], d[1], d[2]))
        # Display probing grid
        elif arglist[0] == 'grid':
            pg = self.Planner.Leveler.probingGrid
            xt = self.Planner.Leveler['probe_tick'][0]
            yt = self.Planner.Leveler['probe_tick'][1]
            if not self.Planner.Leveler.probingGrid.empty():
                print('\n\t:Probing Points ([x, y]):')
                for x in range(0,xt):
                    for y in range(0,yt):
                        print('{}\t'.format(pg.data[x * yt + y]), end='')
                    print('')
            else:
                print('Grid not yet generated.')
        # Invalid argument
        else:
            print('Unrecognized list argument.')
            return
        print('')

    def probe(self, arglist):
        if len(arglist) == 0 or arglist[0] == 'grid':
            # Pull parameters directly off configuration file
            try:
                self.Planner.Leveler.parse_dict(self.pmuConfParser.dict)
            except:
                print(sys.exc_info()[1])
                return
            if (self.Planner.leveling_gen_grid(self.excellonParser.buffer)):
                print('Successfully generated grid.')
            else:
                print('Unable to generate probing grid.')
                return
        elif arglist[0] == 'run':
            # connect to CNC and do physical probing
            pass

    def level(self, arglist):
        b = None
        if len(arglist) == 0 or arglist[0] == 'file':
            b = self.gcodeParser.buffer
        elif arglist[0] == 'buffer':
            b = self.Planner.buffer
        if(self.Planner.leveling_run(b, self.hmapParser.buffer)):
            print('Successfully leveled G-Code.')
        else:
            print('Failed to level G-Code.')

    def view(self, arglist):
        # Pull parameters directly off configuration file
        try:
            self.View.parse_dict(self.pmuConfParser.dict)
        except:
            print(sys.exc_info()[1])
            return
        if   arglist[0] == 'drl':
            self.View.print_drills(self.excellonParser.buffer)
        elif arglist[0] == 'drltol':
            self.View.print_drills(self.excellonParser.buffer, True)
        elif arglist[0] == 'probe':
            self.View.print_probe(self.Planner.buffer)
        elif arglist[0] == 'new':
            self.View.new_window()
        elif arglist[0] == 'clear':
            self.View.clear_plot()
        elif arglist[0] == 'grid':
            self.View.toggle_grid()
        else:
            print('Unrecognized view command {}'.format(arglist[0]))
        # Allows to concatenate more arguments
        if len(arglist) > 1:
            self.view(arglist[1:])

    def print_help(self, arglist):
        # Print root info
        if len(arglist) is 0:
            print('\n{}'.format(self.descriptionText))
            print('\nCommand list:')
            for c in self.commands:
                print('{}'.format(c)+' '*(14-len(c))+'\t{}'.format(self.commands[c]['help']))
            print('')
        # Print detailed description of selected command
        else:
            if arglist[0] not in self.commands:
                print('Unrecognized command {}'.format(arglist[0]))
            elif self.commands[arglist[0]]['desc'] is '':
                print('No further description for command {}'.format(arglist[0]))
            else:
                print(self.commands[arglist[0]]['help'])
                print(self.commands[arglist[0]]['desc'])

    def exit(self, arglist):
        bye = ['Don\'t break your fine endmills.', 'Don\'t home with disabled endstops.',
               'DIY PCB etching is for noobs.', 'Pro tip: try out the esoteric 0-point probing method.',
               'Right angled traces make the PCB-Gods mad.', 'Don\'t scratch your forehead with a running spindle.']
        print(bye[random.randint(0,len(bye)-1)])
        sys.exit(0)

    def register_command(self, fcn, command, help, ddescription='', minargc=0):
        nc = {}
        nc['f']    = fcn
        nc['help'] = help
        nc['desc'] = ddescription
        nc['minc'] = minargc
        self.commands[command] = nc