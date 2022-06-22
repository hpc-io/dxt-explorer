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
works, and perform publicly and display publicly, and to permit others to do
so.
"""

import os
import sys
import csv
import shlex
import argparse
import subprocess
import webbrowser
import logging
import logging.handlers
import pkg_resources
import darshan
import pandas as pd

from distutils.spawn import find_executable
from alive_progress import alive_bar


class Explorer:

    def __init__(self, args):
        """Initialize the explorer."""
        self.args = args

        self.configure_log()
        self.has_dxt_parser()
        self.has_r_support()

    def configure_log(self):
        """Configure the logging system."""
        self.logger = logging.getLogger('DXT Explorer')

        if self.args.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        # Defines the format of the logger
        formatter = logging.Formatter(
            '%(asctime)s %(module)s - %(levelname)s - %(message)s'
        )

        console = logging.StreamHandler()

        console.setFormatter(formatter)

        self.logger.addHandler(console)

    def run(self):
        self.is_darshan_file(self.args.darshan)

        if not self.args.prefix:
            self.prefix = os.getcwd()
        else:
            self.prefix = self.args.prefix

        if self.args.list_files:
            self.list_files(self.args.darshan)

            exit()

        self.generate_plot(self.args.darshan)

        if self.args.transfer:
            self.generate_transfer_plot(self.args.darshan)

        if self.args.spatiality:
            self.generate_spatiality_plot(self.args.darshan)

    def get_directory(self):
        """Determine the install path to find the execution scripts."""
        try:
            root = __file__
            if os.path.islink(root):
                root = os.path.realpath(root)

            return os.path.dirname(os.path.abspath(root))
        except Exception:
            return None

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
            self.logger.debug('darshan-dxt-parser: FOUND')
        else:
            self.logger.error('darshan-dxt-parser: NOT FOUND')

            exit(-1)

    def has_r_support(self):
        """Check if `Rscript` is on PATH."""
        if find_executable('Rscript') is not None:
            self.logger.debug('Rscript: FOUND')
        else:
            self.logger.error('Rscript: NOT FOUND')

            exit(-1)

    def list_files(self, report):
        """Create a dictionary of file id as key and file name as value."""
        file_ids = report.log['name_records']

        for file_id, file_name in file_ids.items():
            self.logger.info('FILE: {} (ID {})'.format(file_name, file_id))

        return file_ids

    def create_dataframe(self, data, file_id, module):
        """Create a dataframe from parsed records."""
        column_names = ['file_id', 'api', 'rank', 'operation', 'segment', 'offset', 'length', 'start_time', 'end_time', 'ost']
        result = pd.DataFrame()
        for i in range(len(data)): 
            if file_id == data[i]['id']:
                if(data[i]['write_count'] > 0):
                    write_segments = data[i]['write_segments']
                    
                    write_segments['file_id'] = file_id

                    write_segments['api'] = module

                    write_segments['rank'] = data[i]['rank']

                    write_segments['operation'] = 'write'    
                    
                    write_segments['ost'] = '' 
                    
                    frames = [result, write_segments]
                    
                    result = pd.concat(frames)
                if(data[i]['read_count'] > 0):    
                    read_segments = data[i]['read_segments']

                    read_segments['file_id'] = file_id

                    read_segments['api'] = module

                    read_segments['rank'] = data[i]['rank']

                    read_segments['operation'] = 'read'  
                    
                    read_segments['ost'] = ''   

                    frames = [result, read_segments]
                    
                    result = pd.concat(frames)   

        result.index.name = 'segment'
                
        result.reset_index(inplace=True)
        
        result = result.reindex(columns=column_names)

        result.rename(columns = {'length':'size', 'start_time':'start', 'end_time':'end'}, inplace = True)
        
        return result

    def subset_dataset(self, file, file_ids, report):
        """Subset the dataset based on file id and save to a csv file."""
        self.logger.info('generating dataframes')
        with alive_bar(total=len(file_ids), title='', stats=False, spinner=None, enrich_print=False) as bar:
            for file_id in file_ids:
                subset_dataset_file = '{}.{}'.format(file, file_id)

                if os.path.exists(subset_dataset_file + '.dxt.csv'):
                    self.logger.debug('using existing parsed Darshan file')

                    bar()
                    continue

                self.logger.debug('parsing POSIX data')                      
                df_posix = report.records['DXT_POSIX'].to_df()
                result = self.create_dataframe(df_posix, file_id, 'POSIX')
                result.to_csv(subset_dataset_file + '.dxt.csv', mode='a', index=False)

                self.logger.debug('parsing MPIIO data')   
                df_mpiio = report.records['DXT_MPIIO'].to_df()
                result = self.create_dataframe(df_mpiio, file_id, 'MPIIO')
                result.to_csv(subset_dataset_file + '.dxt.csv', mode='a', index=False, header=None)
                
                bar()

    def generate_plot(self, file):
        """Generate an interactive operation plot."""
        limits = ''

        if self.args.start:
            limits += ' -s {} '.format(self.args.start)

        if self.args.end:
            limits += ' -e {} '.format(self.args.end)

        if self.args.start_rank:
            limits += ' -n {} '.format(self.args.start_rank)

        if self.args.end_rank:
            limits += ' -m {} '.format(self.args.end_rank)

        report = darshan.DarshanReport(file, read_all=True)

        file_ids = self.list_files(report)

        # Generated the CSV files for each plot
        self.subset_dataset(file, file_ids, report)

        with alive_bar(total=len(file_ids), title='', stats=False, spinner=None, enrich_print=False) as bar:
            for file_id, file_name in file_ids.items():
                output_file = '{}/{}-{}.html'.format(self.prefix, file_id, 'operation')

                path = 'plots/operation.R'
                script = pkg_resources.resource_filename(__name__, path)

                command = '{} -f {}.{}.dxt.csv {} -o {} -x {}'.format(
                    script,
                    file,
                    file_id,
                    limits,
                    output_file,
                    file_name
                )

                args = shlex.split(command)

                self.logger.info('generating interactive operation for: {}'.format(file_name))
                self.logger.debug(command)

                s = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

                if s.returncode == 0:
                    if os.path.exists(output_file):
                        self.logger.info('SUCCESS: {}'.format(output_file))
                    else:
                        self.logger.warning('no data to generate interactive plots')

                    if self.args.browser:
                        webbrowser.open('file://{}'.format(output_file), new=2)
                else:
                    self.logger.error('failed to generate the interactive plots (error %s)', s.returncode)

                    if s.stdout is not None:
                        for item in s.stdout.decode().split('\n'):
                            if item.strip() != '':
                                self.logger.debug(item)

                    if s.stderr is not None:
                        for item in s.stderr.decode().split('\n'):
                            if item.strip() != '':
                                self.logger.error(item)

                bar()

    def generate_transfer_plot(self, file):
        """Generate an interactive transfer plot."""
        limits = ''

        if self.args.start:
            limits += ' -s {} '.format(self.args.start)

        if self.args.end:
            limits += ' -e {} '.format(self.args.end)

        if self.args.start_rank:
            limits += ' -n {} '.format(self.args.start_rank)

        if self.args.end_rank:
            limits += ' -m {} '.format(self.args.end_rank)

        report = darshan.DarshanReport(file, read_all=True)

        file_ids = self.list_files(report)
        
        # Generated the CSV files for each plot
        self.subset_dataset(file, file_ids, report)

        with alive_bar(total=len(file_ids), title='', stats=False, spinner=None, enrich_print=False) as bar:
            for file_id, file_name in file_ids.items():
                output_file = '{}/{}-{}.html'.format(self.prefix, file_id, 'transfer')

                path = 'plots/transfer.R'
                script = pkg_resources.resource_filename(__name__, path)

                command = '{} -f {}.{}.dxt.csv -o {} -x {}'.format(
                    script,
                    file,
                    file_id,
                    output_file,
                    file_name
                )

                args = shlex.split(command)

                self.logger.info('generating interactive transfer for: {}'.format(file_name))
                self.logger.debug(command)

                s = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

                if s.returncode == 0:
                    self.logger.info('SUCCESS: {}'.format(output_file))

                    if self.args.browser:
                        webbrowser.open('file://{}.{}.transfer.html'.format(file, file_id), new=2)
                else:
                    self.logger.error('failed to generate the interactive plots (error %s)', s.returncode)

                    if s.stdout is not None:
                        for item in s.stdout.decode().split('\n'):
                            if item.strip() != '':
                                self.logger.debug(item)

                    if s.stderr is not None:
                        for item in s.stderr.decode().split('\n'):
                            if item.strip() != '':
                                self.logger.error(item)

                bar()

    def generate_spatiality_plot(self, file):
        """Generate an interactive spatiality plot."""
        report = darshan.DarshanReport(file, read_all=True)

        file_ids = self.list_files(report)
        
        # Generated the CSV files for each plot
        self.subset_dataset(file, file_ids, report)

        with alive_bar(total=len(file_ids), title='', stats=False, spinner=None, enrich_print=False) as bar:
            for file_id, file_name in file_ids.items():
                output_file = '{}/{}-{}.html'.format(self.prefix, file_id, 'spatiality')

                path = 'plots/spatiality.R'
                script = pkg_resources.resource_filename(__name__, path)

                command = '{} -f {}.{}.dxt.csv -o {} -x {}'.format(
                    script,
                    file,
                    file_id,
                    output_file,
                    file_name
                )

                args = shlex.split(command)

                self.logger.info('generating interactive spatiality for: {}'.format(file_name))
                self.logger.debug(command)

                s = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

                if s.returncode == 0:
                    if os.path.exists(output_file):
                        self.logger.info('SUCCESS: {}'.format(output_file))
                    else:
                        self.logger.warning('no data to generate spatiality plots')

                    if self.args.browser:
                        webbrowser.open('file://{}'.format(output_file), new=2)
                else:
                    self.logger.error('failed to generate the spatiality plots (error %s)', s.returncode)

                    if s.stdout is not None:
                        for item in s.stdout.decode().split('\n'):
                            if item.strip() != '':
                                self.logger.debug(item)

                    if s.stderr is not None:
                        for item in s.stderr.decode().split('\n'):
                            if item.strip() != '':
                                self.logger.error(item)

                bar()


def main():
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
        help='Output directory'
    )

    PARSER.add_argument(
        '-p',
        '--prefix',
        default=None,
        help='Output directory'
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

    PARSER.add_argument(
        '-d',
        '--debug',
        action='store_true',
        dest='debug',
        help='Enable debug mode'
    )

    PARSER.add_argument(
        '-l',
        '--list',
        action='store_true',
        dest='list_files',
        help='List all the files with trace'
    )

    PARSER.add_argument(
        '--start',
        action='store',
        dest='start',
        help='Report starts from X seconds (e.g., 3.7) from beginning of the job'
    )

    PARSER.add_argument(
        '--end',
        action='store',
        dest='end',
        help='Report ends at X seconds (e.g., 3.9) from beginning of the job'
    )

    PARSER.add_argument(
        '--from',
        action='store',
        dest='start_rank',
        help='Report start from rank N'
    )

    PARSER.add_argument(
        '--to',
        action='store',
        dest='end_rank',
        help='Report up to rank M'
    )

    PARSER.add_argument(
        '--browser',
        default=False,
        action='store_true',
        dest='browser',
        help='Open the browser with the generated plot'
    )

    ARGS = PARSER.parse_args()

    EXPLORE = Explorer(ARGS)
    EXPLORE.run()


if __name__ == '__main__':
    main()
