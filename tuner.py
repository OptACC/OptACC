#!/usr/bin/python
import logging
import math
import os
import re
import subprocess

from nelder_mead import nelder_mead, round_acc, neighbors_acc
from point import Point
from exhaustive_search import exhaustive_search
from utilities import call_command
from testresult import TestResult

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
            source,
            executable='./a.out',
            compile_command=None, # None here implies use of default
            search_method='nelder-mead',
            repetitions=10,
            time_regexp=TIME_RE,
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
def gen_tuning_function(opts):
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

        prefix = '[num_gangs={0:<4.0f}, vector_length={1:<4.0f}]'.format(
                num_gangs, vector_length)

        LOGGER.debug('%s Compiling: %s', prefix, command)

        output, return_code = call_command(command, env=env)
        if return_code != 0:
            LOGGER.error('%s Compile command failed with exit code %d.  '
                    'Skipping this point.  (Compiler output was: "%s")',
                    prefix, return_code, output)
            # Compiler failed, cannot continue
            return TestResult(x, error='Compile command failed')

        results = []
        for i in range(repetitions):
            LOGGER.debug('%s Running %s', prefix, opts.executable)
            output, return_code = call_command(opts.executable)

            if return_code != 0 and not opts.ignore_exit:
                LOGGER.error('%s Command %s failed with exit code %d', prefix,
                        opts.executable, return_code)
                break  # Don't record time; assume subsequent reps will fail

            if opts.kernel_timing:
                match = KERNEL_TIMING_RE.search(output)
                if not match:
                    LOGGER.error('%s Output from %s did not contain PGI '
                            'kernel timing data.  This is likely a problem '
                            'with your program or compile command.  The '
                            'output was: "%s"', prefix, opts.executable,
                            output)
                    return TestResult(x,
                            error='PGI kernel timing data missing')

                time = float(match.group(1).replace(',', '')) * 1e-6
            else:
                match = opts.time_regexp.search(output)
                if not match:
                    LOGGER.error('%s Output from %s did not contain timing '
                            ' data.  This is likely a problem with your '
                            'program or output regex "%s".  The '
                            'output was: "%s"', prefix, opts.executable,
                            opts.time_regexp.pattern, output)
                    return TestResult(x, error='Timing data missing')

                time = match.group(1)

            time = float(time)
            LOGGER.debug('%s Time: %f', prefix, time)
            results.append(time)

        if len(results) == 0:  # Executable terminated with nonzero exit code
            return TestResult(x, error='Executable failed')
        else:
            n = len(results)
            avg = sum(results) / n
            if n == 1: # Avoid ZeroDivisionError
                stdev = 0
            else:
                stdev = math.sqrt(
                        sum((x - avg)**2 for x in results) / float(n - 1))

            LOGGER.info('%s Average: %.4f, Standard Deviation: %.4f', prefix,
                    avg, stdev)
            return TestResult(x, avg, stdev)
    return fn

def tune(opts):
    run_test = gen_tuning_function(opts)

    def objective(x):
        out_of_range = TestResult(x, error='Point out of range')
        if x[0] < opts.num_gangs_min or x[0] > opts.num_gangs_max:
            return out_of_range

        if x[1] < opts.vector_length_min or x[1] > opts.vector_length_max:
            return out_of_range

        return run_test(x, repetitions=opts.repetitions)

    if opts.search_method == 'nelder-mead':
        # Set initial guess to what the compiler usually assumes
        # num_gangs(256) vector_length(128)
        init = Point(256, 128)
        res = nelder_mead(objective, init, neighbors_acc, round_acc)
    elif opts.search_method == 'exhaustive':
        # Exhaustive search: search powers of 2 within gang/vector ranges
        def ilog2(x):
            return int(math.floor(math.log(x, 2)))
        def generator():
            gmin = ilog2(opts.num_gangs_min)
            gmax = ilog2(opts.num_gangs_max)
            vmin = ilog2(opts.vector_length_min)
            vmax = ilog2(opts.vector_length_max)
            for gang_pow2 in range(gmin, gmax+1): # +1 since range is exclusive
                for vec_pow2 in range(vmin, vmax+1):
                    yield Point(1 << gang_pow2, 1 << vec_pow2)
        res = exhaustive_search(objective, generator())
    else:
        raise RuntimeError('Unknown search method "{0}"'.format(
                opts.search_method))

    LOGGER.info('-- RESULTS --')
    for point in sorted(res.tests, key=lambda x: res.tests[x], reverse=True):
        result = res.tests[point]
        LOGGER.info(str(result))
    LOGGER.info('-------------')
    LOGGER.info('Tested %d points', len(res.tests))
    LOGGER.info('Search took %d iterations', res.num_iterations)
    LOGGER.info('Optimal result: %s', str(res.tests[res.optimal]))

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Autotune an OpenACC program')
    parser.add_argument('source', type=str)
    parser.add_argument('-e', '--executable', type=str)
    parser.add_argument('-c', '--compile-command', type=str)
    parser.add_argument('-s', '--search-method', type=str)
    parser.add_argument('-r', '--repetitions', type=int)
    parser.add_argument('-t', '--time-regexp', type=str)
    parser.add_argument('-k', '--kernel-timing', action='store_true')
    parser.add_argument('-l', '--logfile', type=str)
    parser.add_argument('--num-gangs-min', type=int)
    parser.add_argument('--num-gangs-max', type=int)
    parser.add_argument('--vector-length-min', type=int)
    parser.add_argument('--vector-length-max', type=int)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-x', '--ignore-exit', action='store_true')

    args = parser.parse_args()

    # Extract provided arguments into a dictionary for easy construction
    # of TuningOptions
    kwargs = dict( (k, args.__dict__[k]) for k in args.__dict__
            if args.__dict__[k] != None )

    t = TuningOptions(**kwargs)

    LOGGER.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
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
    tune(t)

if __name__ == '__main__':
    main()
