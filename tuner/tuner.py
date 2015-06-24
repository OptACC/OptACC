import csv
import logging
import math
import os
import re
import sys

from .result_writer import ResultFiles, ResultWriter
from .point import Point
from .utilities import call_command
from .testresult import TestResult

from .methods.nelder_mead import tune as tune_nelder_mead
from .methods.coord_search import tune_coord_search
from .methods.grid_search import (tune_grid_pow2, tune_grid_32,
        tune_grid_64, tune_grid_128, tune_grid_256,
        tune_grid_32_vlpow2)

METHODS = {
    'nelder-mead': tune_nelder_mead,
    'coord-search': tune_coord_search,
    'grid-pow2': tune_grid_pow2,
    'grid32': tune_grid_32,
    'grid64': tune_grid_64,
    'grid128': tune_grid_128,
    'grid256': tune_grid_256,
    'grid32-vlpow2': tune_grid_32_vlpow2
}

KERNEL_TIMING_RE = re.compile(r'Accelerator Kernel Timing data\n'
        r'(?:[^\n]*\n){2}'
        r'\s*time\(us\): ([\d,]+)')

LOGGER = logging.getLogger('tuner')

def _gen_tuning_function(opts, output_writer):
    '''Generates a tunable objective function based on the given options

    opts -- TuningOptions representing the tuning parameters
    output_writer -- OutputWriter to record results of tuning

    Returns a function fn(x, repetitions=1), where x is the input tuple and
    repetitions represents how many times to run the program.
    '''

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

def _load_testing_data(csv_filename):
    '''Loads data points from a CSV file

    The format of the file must be the same as those generated by the
    --write-csv flag for the tuner.

    Returns a dictionary mapping (num_gangs, vector_length) pairs to the
    timing data for that point.
    '''

    LOGGER.info('TEST MODE - Using timing data from CSV file %s', csv_filename)
    csv_data = {}
    with open(csv_filename) as csvfile:
        try:
            reader = csv.DictReader(csvfile)
            for row in reader:
                for key in ['num_gangs', 'vector_length', 'time', 'stdev']:
                    if row[key] is None:
                        raise KeyError(key)

                key = Point(row['num_gangs'], row['vector_length'])
                values = { 'time': float(row['time']),
                           'stdev': float(row['stdev']),
                           'error msg': row['error msg'] }
                csv_data[key] = values
        except KeyError as e:
            LOGGER.error('Invalid CSV file format: missing column %s', str(e))
            sys.exit(1)
        except ValueError as e:
            LOGGER.error('Error in CSV file %s, line %d: %s',
                  csv_filename, reader.line_num, e)
            sys.exit(1)
    LOGGER.info('            Loaded %d data points', len(csv_data))

    # Find the best and worst points in the loaded data
    sdata = sorted(csv_data, key=lambda x: csv_data[x]['time'])
    best = sdata[0]
    worst = sdata[len(sdata)-1]
    LOGGER.info(u'            Minimum: %s: %f \u00B1 %f',
                best, csv_data[best]['time'], csv_data[best]['stdev'])
    LOGGER.info(u'            Maximum: %s: %s \u00B1 %f',
                worst, csv_data[worst]['time'], csv_data[worst]['stdev'])

    known_best_result = TestResult(point=best,
                                   average=csv_data[best]['time'],
                                   stdev=csv_data[best]['stdev'],
                                   error=csv_data[best]['error msg'])

    def percentile(time):
        n = len(sdata)
        count = 0
        for i in range(n):
            if csv_data[sdata[i]]['time'] <= time:
                count += 1
            else:
                break
        return int(round(float(count) / n * 100))

    return csv_data, known_best_result, percentile

def _gen_csv_function(csv_filename, output_writer):
    '''Generates a tunable objective function from a CSV file

    Analagous to _gen_tuning_function but for operating on prerecorded CSV
    data.
    '''

    csv_data, known_best, percentile = _load_testing_data(csv_filename)
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
    return fn, known_best, percentile

def tune(opts, output_writer):
    '''Tunes an input program based on the TuningOptions provided'''
    known_best = percentile = None
    if opts.source is not None and opts.source.endswith(".csv"):
        run_test, known_best, percentile = _gen_csv_function(opts.source,
                output_writer)
    else:
        run_test = _gen_tuning_function(opts, output_writer)

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
    LOGGER.info('Best result found: %s', str(res.tests[res.optimal]))
    if known_best is not None and percentile is not None:
        LOGGER.info('Optimal result from test data: %s', str(known_best))
        LOGGER.info('Percentile of best result: %d%%',
            percentile(res.tests[res.optimal].average))
        try:
            if known_best.is_signif_diff(res.tests[res.optimal], opts.repetitions):
                LOGGER.warn('BEST RESULT FOUND DIFFERS FROM OPTIMAL RESULT')
            else:
                LOGGER.info('(No statistically significant difference)')
        except (ValueError, ZeroDivisionError) as e:
            # T-test will fail if standard deviation is 0 or number of points
            # is 0.  It isn't important, so don't die.
            LOGGER.warn('Unable to perform T-test (%s)', e)

    # Do this afterward, in case writing files fails
    output_writer.write_result(res, opts.repetitions)
