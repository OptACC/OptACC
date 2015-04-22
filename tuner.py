#!/usr/bin/python

from __future__ import print_function

import logging
import sys
import tuner

LOGGER = logging.getLogger('tuner')

def main():
    try:
        import argparse
    except ImportError as e:
        # Python 2.6 does not provide argparse in the standard library
        # so load a local copy (taken from Python 2.7)
        import argparseshim as argparse

    parser = argparse.ArgumentParser(description='Autotune an OpenACC program')
    parser.add_argument('source', type=str, nargs='?',
            help='name of a source file to pass to the compile command',
            metavar='filename')
    parser.add_argument('-e', '--executable', type=str,
            help='executable to run (default: ./a.out)',
            metavar='filename')
    parser.add_argument('-c', '--compile-command', type=str,
            help='command line to compile an executable',
            metavar='command')
    parser.add_argument('-a', '--use-heuristic', action='store_true',
            help='use a heuristic to avoid autotuning if it is unlikely to ' +
                 'be beneficial')
    parser.add_argument('-s', '--search-method', type=str,
            help='search method to use when choosing test points: ' +
                 ', '.join(sorted(tuner.METHODS.keys())),
            metavar='method')
    parser.add_argument('-r', '--repetitions', type=int,
            help='number of times to run the executable to collect timing info',
            metavar='count')
    parser.add_argument('-t', '--time-regexp', type=str,
            help='regular expression to identify timing information in the ' +
                 'output produced by the executable',
            metavar='regexp')
    parser.add_argument('-k', '--kernel-timing', action='store_true',
            help='search the output for timing information produced when a ' +
                 'program is compiled with "-ta=nvidia,time" using pgcc/pgf90')
    parser.add_argument('-l', '--logfile', type=str,
            help='write log messages to a file',
            metavar='filename.log')
    parser.add_argument('--write-gnuplot', type=str,
            help='generate a Gnuplot script to visualize the test results',
            metavar='filename.gp')
    parser.add_argument('--write-csv', type=str,
            help='write timing results line by line to a CSV file',
            metavar='filename.csv')
    parser.add_argument('--write-spreadsheet', type=str,
            help='write an Excel XML spreadsheet with results and statistics',
            metavar='filename.xml')
    parser.add_argument('--num-gangs-min', type=int,
            help='minimum allowable value of num_gangs',
            metavar='value')
    parser.add_argument('--num-gangs-max', type=int,
            help='maximum allowable value of num_gangs',
            metavar='value')
    parser.add_argument('--vector-length-min', type=int,
            help='minimum allowable value of vector_length',
            metavar='value')
    parser.add_argument('--vector-length-max', type=int,
            help='maximum allowable value of vector_length',
            metavar='value')
    parser.add_argument('-v', '--verbose', action='store_true',
            help='display progress and diagnostic information while tuning')
    parser.add_argument('-x', '--ignore-exit', action='store_true',
            help='continue with autotuning even if the executable exits ' +
                 'with a nonzero exit code')

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

    t = tuner.TuningOptions(**kwargs)

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
    with tuner.ResultWriter(tuner.ResultFiles(args.write_gnuplot,
                                  args.write_csv,
                                  args.write_spreadsheet)) as w:
        tuner.tune(t, w)

if __name__ == '__main__':
    main()
