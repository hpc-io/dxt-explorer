#!/usr/bin/python3

"""
DXT Explorer.

DXT Explorer Copyright (c) 2021, The Regents of the University of
California, through Lawrence Berkeley National Laboratory (subject
to receipt of any required approvals from the U.S. Dept. of Energy). 
All rights reserved.

If you have questions about your rights to use or distribute this software,
please contact Berkeley Lab's Intellectual Property Office at
IPO@lbl.gov.

NOTICE.  This Software was developed under funding from the U.S. Department
of Energy and the U.S. Government consequently retains certain rights.  As
such, the U.S. Government has been granted for itself and others acting on
its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the
Software to reproduce, distribute copies to the public, prepare derivative 
works, and perform publicly and display publicly, and to permit others to do so.
"""

import os
import sys
import csv
import shlex
import argparse
import subprocess
import logging
import logging.handlers

import pandas as pd

from plotnine import *
from distutils.spawn import find_executable


class Explorer:

    def __init__(self, args):
        """Initialize the explorer."""
        self.configure_log()
        self.has_dxt_parser()

        self.args = args

    def configure_log(self):
        """Configure the logging system."""
        self.logger = logging.getLogger('DXT Explorer')
        self.logger.setLevel(logging.DEBUG)

        # Defines the format of the logger
        formatter = logging.Formatter('%(asctime)s %(module)s - %(levelname)s - %(message)s')

        console = logging.StreamHandler()
        
        console.setFormatter(formatter)

        self.logger.addHandler(console)

    def run(self):
        self.is_darshan_file(self.args.darshan)

        self.parse(self.args.darshan)
        self.generate_plot(self.args.darshan)

        if self.args.transfer:
            self.generate_transfer_plot(self.args.darshan)

        if self.args.spatiality:
            self.generate_spatiality_plot(self.args.darshan)


    def is_darshan_file(self, file):
        """Check if the provided file exists and is a .darshan file."""
        if not os.path.exists(self.args.darshan):
            self.logger.error('{}: NOT FOUND'.format(file))

            exit(-1)

        if not self.args.darshan.endswith('.darshan'):
            self.logger.error('{} is not a .darshan file'.format(file))

            exit(-1)


    def has_dxt_parser(self):
        """Check if `darshan-dxt-parser` is on PATH."""
        if find_executable('darshan-dxt-parser') is not None:
            self.logger.info('darshan-dxt-parser: FOUND')
        else:
            self.logger.error('darshan-dxt-parser: NOT FOUND')

            exit(-1)

    def dxt(self, file):
        """Parse the Darshan file to generate the .dxt trace file."""
        command = 'darshan-dxt-parser {0}'.format(file)

        args = shlex.split(command)

        self.logger.info('parsing {} file'.format(file))

        with open('{}.dxt'.format(file), 'w') as output:
            s = subprocess.run(args, stderr=subprocess.PIPE, stdout=output)

        assert(s.returncode == 0)


    def parse(self, file):
        """Parse the .darshan.dxt file to generate a CSV file."""
        self.dxt(file)

        self.logger.info('generating an intermediate CSV file')

        with open(file + '.dxt') as f:
            lines = f.readlines()
            file_id = None
            file_name = None

            with open(file + '.dxt.csv', 'w', newline='') as csvfile:
                w = csv.writer(csvfile)

                w.writerow([
                    'file_id',
                    'api',
                    'rank',
                    'operation',
                    'segment',
                    'offset',
                    'size',
                    'start',
                    'end'
                ])

                for line in lines:
                    if 'file_id' in line:
                        file_id = line.split(',')[1].split(':')[1].strip()
                        file_name = line.split(',')[2].split(':')[1].strip()

                    if 'X_POSIX' in line:
                        info = line.replace('[', '').replace(']', '').split()

                        api = info[0]
                        rank = info[1]
                        operation = info[2]
                        segment = info[3]
                        offset = info[4]
                        size = info[5]
                        start = info[6]
                        end = info[7]

                        w.writerow([
                            file_id,
                            api.replace('X_', ''),
                            rank,
                            operation,
                            segment,
                            offset,
                            size,
                            start,
                            end
                        ])

                    if 'X_MPIIO' in line:
                        info = line.split()

                        api = info[0]
                        rank = info[1]
                        operation = info[2]

                        # Newer Darshan DXT logs have segment for MPI-IO
                        if len(info) == 8:
                            segment = info[3]
                            offset = info[4]
                            size = info[5]
                            start = info[6]
                            end = info[7]
                        else:
                            segment = -1;
                            offset = info[3]
                            size = info[4]
                            start = info[5]
                            end = info[6]

                        w.writerow([
                            file_id,
                            api.replace('X_', ''),
                            rank,
                            operation,
                            segment,
                            offset,
                            size,
                            start,
                            end
                        ])


    def generate_plot(self, file):
        """Generate an interactive operation plot."""
        command = 'plots/operation.R -f {0}.dxt.csv'.format(file)

        args = shlex.split(command)

        self.logger.info('generating interactive operation plot')

        s = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        assert(s.returncode == 0)

    def generate_transfer_plot(self, file):
        """Generate an interactive transfer plot."""
        command = 'plots/transfer.R -f {0}.dxt.csv'.format(file)

        args = shlex.split(command)

        self.logger.info('generating interactive transfer plot')

        s = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        assert(s.returncode == 0)

    def generate_spatiality_plot(self, file):
        """Generate an interactive spatiality plot."""
        command = 'plots/spatiality.R -f {0}.dxt.csv'.format(file)

        args = shlex.split(command)

        self.logger.info('generating interactive spatiality plot')

        s = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        assert(s.returncode == 0)



PARSER = argparse.ArgumentParser(
    description='DXT Explorer: '
)

PARSER.add_argument(
    'darshan', 
    help='Input .darshan file'
)

PARSER.add_argument(
    '-o',
    '--output',
    default=sys.stdout,
    type=argparse.FileType('w'),
    help='Name of the output file'
)

PARSER.add_argument(
    '-t',
    '--transfer',
    default=False,
    action='store_true',
    help='Generate an interactive data transfer explorer'
)

PARSER.add_argument(
    '-s',
    '--spatiality',
    default=False,
    action='store_true',
    help='Generate an interactive spatiality explorer'
)


ARGS = PARSER.parse_args()

EXPLORE = Explorer(ARGS)
EXPLORE.run()
