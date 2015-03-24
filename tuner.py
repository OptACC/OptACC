#!/usr/bin/python

from __future__ import print_function

import csv
import logging
import math
import os
import re
import subprocess
import sys

from result_writer import ResultFiles, ResultWriter
from point import Point
from utilities import call_command
from testresult import TestResult

from methods.nelder_mead import tune as tune_nelder_mead
from methods.exhaustive_search import (tune_exhaustive_pow2, tune_exhaustive_32,
        tune_exhaustive_64, tune_exhaustive_128, tune_exhaustive_256)

METHODS = {
    'nelder-mead': tune_nelder_mead,
    'exhaustive-pow2': tune_exhaustive_pow2,
    'exhaustive32': tune_exhaustive_32,
    'exhaustive64': tune_exhaustive_64,
    'exhaustive128': tune_exhaustive_128,
    'exhaustive256': tune_exhaustive_256
}

LOGGER = logging.getLogger('tuner')

# Default compilation command
PGCC_COMPILE = ('pgcc -acc -DNUM_GANGS={num_gangs} '
                '-DVECTOR_LENGTH={vector_length} {source}')
PGCC_COMPILE_KERNEL_TIMING = ('pgcc -acc -DNUM_GANGS={num_gangs} '
                '-DVECTOR_LENGTH={vector_length} -ta=nvidia,time {source}')

# Default regular expression matching the time output
TIME_RE = r'(?:time)[=:\s]*([\d.]+)'
KERNEL_TIMING_RE = re.compile(r'Accelerator Kernel Timing data\n'
        r'(?:[^\n]*\n){2}'
        r'\s*time\(us\): ([\d,]+)')

class TuningOptions(object):
    ''' Represents a set of options and constraints for tuning '''
    def __init__(self,
            source=None,
            executable='./a.out',
            compile_command=None, # None here implies use of default
            search_method='nelder-mead',
            repetitions=10,
            time_regexp=TIME_RE,
            write_gnuplot=None,
            write_csv=None,
            write_spreadsheet=None,
            num_gangs_min=2,
            num_gangs_max=1024,
            vector_length_min=2,
            vector_length_max=1024,
            verbose=False,
            ignore_exit=False,
            kernel_timing=False,
            **kwargs):

        self.source = source
        self.executable = executable
        if compile_command:
            self.compile_command = compile_command
        elif kernel_timing:
            self.compile_command = PGCC_COMPILE_KERNEL_TIMING
        else:
            self.compile_command = PGCC_COMPILE
        self.search_method = search_method
        self.repetitions = repetitions
        self.time_regexp = re.compile(time_regexp, re.I)
        self.write_gnuplot = write_gnuplot
        self.write_csv = write_csv
        self.write_spreadsheet = write_spreadsheet
        self.num_gangs_min = num_gangs_min
        self.num_gangs_max = num_gangs_max
        self.vector_length_min = vector_length_min
        self.vector_length_max = vector_length_max
        self.verbose = verbose
        self.ignore_exit = ignore_exit
        self.kernel_timing = kernel_timing

# From a set of tuning options, return a function that when called with a
# num_gangs, vector_length, and optionally a number of repetitions (N), will
# compile the source, run the output N times, and return a list of N results.
# If the compiler or program fails or the output does not match the given time
# regular expression, an exception will be raised.
def gen_tuning_function(opts, output_writer):
    def fn(x, repetitions=1):
        num_gangs, vector_length = map(int, x)
        command = opts.compile_command.format(
                source=opts.source,
                num_gangs=num_gangs,
                vector_length=vector_length
        )

        # Set NUM_GANGS and VECTOR_LENGTH as environment variables so that
        # Makefiles can make use of these parameters.
        env = {
            'NUM_GANGS': str(num_gangs),
            'VECTOR_LENGTH': str(vector_length)
        }

        # Copy environment variables for this process.  This is necessary to
        # preserve $PATH and other variables that might be necessary for
        # compilation.
        env.update(os.environ)

        prefix = '[num_gangs:{0:>4.0f}, vector_length:{1:>4.0f}]'.format(
                num_gangs, vector_length)

        LOGGER.debug('%s Compiling: %s', prefix, command)

        output, return_code = call_command(command, env=env)
        if return_code != 0:
            LOGGER.error('%s Compile command failed with exit code %d.  '
                    'Skipping this point.  (Compiler output was: "%s")',
                    prefix, return_code, output)
            # Compiler failed, cannot continue
            result = TestResult(x, error='Compile command failed')
            output_writer.add(result)
            return result

        result = None
        results = []
        for i in range(repetitions):
            LOGGER.debug('%s Running %s', prefix, opts.executable)
            output, return_code = call_command(opts.executable)

            if return_code != 0 and not opts.ignore_exit:
                LOGGER.error('%s Command %s failed with exit code %d', prefix,
                        opts.executable, return_code)
                result = TestResult(x, error='Executable failed')
                break  # Don't record time; assume subsequent reps will fail

            if opts.kernel_timing:
                match = KERNEL_TIMING_RE.search(output)
                if not match:
                    LOGGER.error('%s Output from %s did not contain PGI '
                            'kernel timing data.  This is likely a problem '
                            'with your program or compile command.  The '
                            'output was: "%s"', prefix, opts.executable,
                            output)
                    result = TestResult(x,
                            error='PGI kernel timing data missing')
                    break

                time = float(match.group(1).replace(',', '')) * 1e-6
            else:
                match = opts.time_regexp.search(output)
                if not match:
                    LOGGER.error('%s Output from %s did not contain timing '
                            ' data.  This is likely a problem with your '
                            'program or output regex "%s".  The '
                            'output was: "%s"', prefix, opts.executable,
                            opts.time_regexp.pattern, output)
                    result = TestResult(x, error='Timing data missing')
                    break

                time = match.group(1)

            time = float(time)
            LOGGER.debug('%s Time: %f', prefix, time)
            results.append(time)
            output_writer.log_run(x, time)

        if result is None:
            if not results:
                result = TestResult(x, error='No points tested')
            else:
                n = len(results)
                avg = sum(results) / n
                if n == 1: # Avoid ZeroDivisionError
                    stdev = 0
                else:
                    stdev = math.sqrt(
                            sum((x - avg)**2 for x in results) / float(n - 1))
                LOGGER.info('%s Average: %f, Standard Deviation: %f', prefix,
                        avg, stdev)
                result = TestResult(x, avg, stdev)

        output_writer.add(result)
        return result
    return fn

# Loads data points from a CSV file (previously written using the --write-csv
# command line option) and returns a dictionary mapping
# (num_gangs, vector_length) pairs to the timing data for that point.
def load_testing_data(csv_filename):
    LOGGER.info('TEST MODE - Using timing data from CSV file %s', csv_filename)
    csv_data = {}
    with open(csv_filename) as csvfile:
        try:
            reader = csv.DictReader(csvfile)
            for row in reader:
                key = Point(row['num_gangs'], row['vector_length'])
                values = { 'time': float(row['time']),
                           'stdev': float(row['stdev']),
                           'error msg': row['error msg'] }
                csv_data[key] = values
        except KeyError, e:
            LOGGER.error('Invalid CSV file format: missing column %s', str(e))
            sys.exit(1)
        except ValueError, e:
            LOGGER.error('Error in CSV file %s, line %d: %s',
                  csv_filename, reader.line_num, e)
            sys.exit(1)
    LOGGER.info('            Loaded %d data points', len(csv_data))
    return csv_data

# From a set of tuning options, return a function that when called with a
# num_gangs and vector_length will return a test result based on prior data
# cached in a CSV file.
def gen_testing_function(csv_filename, output_writer):
    csv_data = load_testing_data(csv_filename)
    def fn(x, repetitions=1):
        num_gangs, vector_length = map(int, x)

        prefix = '[num_gangs:{0:>4.0f}, vector_length:{1:>4.0f}]'.format(
                num_gangs, vector_length)

        result = None
        if x not in csv_data:
            msg = '{0} not in CSV data'.format(x)
            result = TestResult(x, error=msg)
            LOGGER.error('%s', msg)
        elif csv_data[x]['error msg'] is not None:
            result = TestResult(x, error=csv_data[x]['error msg'])
        else:
            avg = csv_data[x]['time']
            stdev = csv_data[x]['stdev']
            LOGGER.info('%s Average: %f, Standard Deviation: %f', prefix,
                avg, stdev)
            result = TestResult(x, avg, stdev)

        output_writer.add(result)
        return result
    return fn

def tune(opts, output_writer):
    if opts.source is not None and opts.source.endswith(".csv"):
        run_test = gen_testing_function(opts.source, output_writer)
    else:
        run_test = gen_tuning_function(opts, output_writer)

    def objective(x):
        out_of_range = TestResult(x, error='Point out of range')
        if x[0] < opts.num_gangs_min or x[0] > opts.num_gangs_max:
            return out_of_range

        if x[1] < opts.vector_length_min or x[1] > opts.vector_length_max:
            return out_of_range

        return run_test(x, repetitions=opts.repetitions)

    if opts.search_method not in METHODS:
        raise RuntimeError('Unknown search method "{0}"'.format(
                opts.search_method))

    res = METHODS[opts.search_method](objective, opts)

    LOGGER.info('-- RESULTS --')
    for point in sorted(res.tests, key=lambda x: res.tests[x], reverse=True):
        result = res.tests[point]
        LOGGER.info(str(result))
    LOGGER.info('-------------')
    LOGGER.info('Tested %d points', len(res.tests))
    LOGGER.info('Search took %d iterations', res.num_iterations)
    LOGGER.info('Optimal result: %s', str(res.tests[res.optimal]))

    # Do this afterward, in case writing files fails
    output_writer.write_result(res, opts.repetitions)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Autotune an OpenACC program')
    parser.add_argument('source', type=str, nargs='?')
    parser.add_argument('-e', '--executable', type=str)
    parser.add_argument('-c', '--compile-command', type=str)
    parser.add_argument('-s', '--search-method', type=str,
            choices=sorted(METHODS.keys()),
            help='Search method to use when choosing test points')
    parser.add_argument('-r', '--repetitions', type=int)
    parser.add_argument('-t', '--time-regexp', type=str)
    parser.add_argument('-k', '--kernel-timing', action='store_true')
    parser.add_argument('-l', '--logfile', type=str,
            help='Write log messages to a file')
    parser.add_argument('--write-gnuplot', type=str,
            help='Generate a Gnuplot script to visualize the test results',
            metavar='filename.gp')
    parser.add_argument('--write-csv', type=str,
            help='Write results line by line to a CSV file',
            metavar='filename.csv')
    parser.add_argument('--write-spreadsheet', type=str,
            help='Write an Excel XML file containing results and statistics',
            metavar='filename.xml')
    parser.add_argument('--num-gangs-min', type=int)
    parser.add_argument('--num-gangs-max', type=int)
    parser.add_argument('--vector-length-min', type=int)
    parser.add_argument('--vector-length-max', type=int)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-x', '--ignore-exit', action='store_true')

    args = parser.parse_args()

    # Sanity check args
    if not args.source and not args.compile_command:
        print('No source file specified.  Please specify a source file or '
              'a custom --compile-command.  See --help for more details',
                file=sys.stderr)
        sys.exit(1)

    if args.num_gangs_min is not None and args.num_gangs_min <= 0 or (
            args.vector_length_min is not None and args.vector_length_min <= 0):
        print('--num-gangs-min and --vector-length-min must be > 0',
                file=sys.stderr)
        sys.exit(1)

    if args.repetitions is not None and args.repetitions <= 0:
        print('--repetitions must be > 0', file=sys.stderr)
        sys.exit(1)

    # Extract provided arguments into a dictionary for easy construction
    # of TuningOptions
    kwargs = dict( (k, args.__dict__[k]) for k in args.__dict__
            if args.__dict__[k] != None )

    t = TuningOptions(**kwargs)

    LOGGER.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s\t%(message)s',
        '%H:%M:%S')
    # Set up console logger
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    LOGGER.addHandler(console)

    # Set up logfile if specified
    if args.logfile:
        file_log = logging.FileHandler(args.logfile)
        file_log.setFormatter(formatter)
        LOGGER.addHandler(file_log)

    LOGGER.debug('TuningOptions: %s', t.__dict__)

    # Set up output data files
    with ResultWriter(ResultFiles(args.write_gnuplot,
                                  args.write_csv,
                                  args.write_spreadsheet)) as w:
        tune(t, w)

if __name__ == '__main__':
    main()
