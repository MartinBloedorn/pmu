#!python

# System imports
import argparse
from argparse import RawTextHelpFormatter
import sys

# PMU imports
from pmu_cli import *

if __name__ == '__main__':
    versionString = 'v2.0.0'
    descriptionText = ('PCB Milling Utility {}\n\n'
                      'Probe or load a heightmap of the PCB you wish to mill.\n'
                      'Then load the GCode that will be fitted to the surface\'s irregularities.'.format(versionString))

    parser = argparse.ArgumentParser(description=descriptionText, formatter_class=RawTextHelpFormatter)
    parser.add_argument('-c', '--conf',    help='PMU configuration filename. If omited, pmu.conf will be loaded.')
    parser.add_argument('-v', '--version', help='Display version.', action='store_true')
    args = parser.parse_args()

    if args.version:
        print('PMU {}'.format(versionString))
        sys.exit()

    cli = pmuCLI()
    cli.descriptionText = descriptionText
    cli.versionString = versionString
    cli.confFilePath = args.conf if args.conf is not None else 'pmu.conf'
    cli.run()


