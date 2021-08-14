#!/usr/bin/env python3

"""
Explore DXT parser.
"""

import os
import sys
import csv
import shlex
import argparse
import subprocess

import pandas as pd

from plotnine import *
from distutils.spawn import find_executable


def main(arguments):

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('darshan', help="Input .darshan file")
    parser.add_argument('-o', '--outfile', help="Output file",
                        default=sys.stdout, type=argparse.FileType('w'))
    parser.add_argument('-t', '--transfer', help="Generate an interactive transfer explorer",
                        default=False, action='store_true')
    parser.add_argument('-s', '--spacial', help="Generate an interactive spatiality explorer",
                        default=False, action='store_true')

    args = parser.parse_args(arguments)

    if not os.path.exists(args.darshan):
        print('ERROR')
        exit()

    parse(args.darshan)
    generate_plot(args.darshan)

    if args.transfer:
        generate_transfer_plot(args.darshan)

    if args.spacial:
        generate_spacial_plot(args.darshan)


def has_dxt_parser():
    """Check whether `darshan-dxt-parser` is on PATH."""

    return find_executable('darshan-dxt-parser') is not None


def dxt(file):
    """Parse the Darshan file to generate the .dxt trace file."""

    assert(has_dxt_parser() == True)

    # Generate the DXT file
    command = 'darshan-dxt-parser {0}'.format(file)

    args = shlex.split(command)

    with open('{}.dxt'.format(file), 'w') as output:
        s = subprocess.run(args, stderr=subprocess.PIPE, stdout=output)

    assert(s.returncode == 0)


def parse(file):
    dxt(file)

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


def generate_plot(file):
    command = './plot.R -f {0}.dxt.csv'.format(file)

    args = shlex.split(command)

    s = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    assert(s.returncode == 0)

def generate_transfer_plot(file):
    command = './plot-transfer.R -f {0}.dxt.csv'.format(file)

    args = shlex.split(command)

    s = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    assert(s.returncode == 0)

def generate_spacial_plot(file):
    command = './plot-spatiality.R -f {0}.dxt.csv'.format(file)

    args = shlex.split(command)

    s = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    assert(s.returncode == 0)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
