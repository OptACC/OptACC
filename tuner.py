from __future__ import print_function
import re
import subprocess
from nelder_mead import *

# Default compilation command
PGCC_COMPILE = ('pgcc -acc -DNUM_GANGS={num_gangs} '
                '-DVECTOR_LENGTH={vector_length} {source}')

# Default regular expression matching the time output
TIME_RE = r'(?:time)[=:\s]*([\d.]+)'

def check_output(cmd):
    handle = subprocess.Popen(cmd, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, shell=True)
    stdout, _ = handle.communicate()
    return stdout.encode('utf8')

class TuningOptions(object):
    ''' Represents a set of options and constraints for tuning '''
    def __init__(self,
            source,
            executable='./a.out',
            compile_command=None, # None here implies use of default
            repetitions=10,
            time_regexp=TIME_RE,
            num_gangs_min=1,
            num_gangs_max=1024,
            vector_length_min=1,
            vector_length_max=1024,
            verbose=False,
            method='Random Search'):

        self.source = source
        self.executable = executable
        self.compile_command = (compile_command or PGCC_COMPILE)
        self.repetitions = repetitions
        self.time_regexp = re.compile(time_regexp, re.I)
        self.num_gangs_min = num_gangs_min
        self.num_gangs_max = num_gangs_max
        self.vector_length_min = vector_length_min
        self.vector_length_max = vector_length_max
        self.verbose = verbose
        self.method = method

# From a set of tuning options, return a function that when called with a
# num_gangs, vector_length, and optionally a number of repetitions (N), will
# compile the source, run the output N times, and return a list of N results.
# If the compiler or program fails or the output does not match the given time
# regular expression, an exception will be raised.
def gen_tuning_function(opts):
    def fn(num_gangs, vector_length, repetitions=1):
        command = opts.compile_command.format(
                source=opts.source,
                num_gangs=num_gangs,
                vector_length=vector_length
        )

        if opts.verbose:
            print('[{0}, {1}] {2}'.format(num_gangs, vector_length, command))
        subprocess.check_call(command, shell=True)

        results = []
        for i in range(repetitions):
            if opts.verbose:
                print('[{0}, {1}] {2}'.format(num_gangs, vector_length,
                        opts.executable))
            result = check_output(opts.executable)

            match = opts.time_regexp.search(result)
            if not match:
                raise RuntimeError('Output from executable {0} did not contain '
                        'any matches for the time regex {1}: {2}'.format(
                        opts.executable, opts.time_regexp.pattern, result))

            time = match.group(1)
            results.append(float(time))

        return sum(results) / len(results)
    return fn

def tune_scipy(opts):
    run_test = gen_tuning_function(opts)

    def objective(x):
        x = map(int, x)
        if opts.verbose:
            print('OBJECTIVE', x)

        if not 1 <= x[0] <= 1024 or not 1 <= x[1] <= 1024:
            return float('+inf')

        return run_test(x[0], x[1], repetitions=opts.repetitions)

    # Set initial guess to what the compiler usually assumes
    # num_gangs(256) vector_length(128)
    init = Point(256, 128)
    res = nelder_mead(objective, init, neighbors_acc, round_acc)
    for point in reversed(sorted(res.tests, key=lambda x: res.tests[x])):
        time = res.tests[point]
        print('num_gangs={0:<6.0f} vector_length={1:<6.0f} => time {2:.4f}'.format(
            point[0], point[1], time))
    print('--------------')
    print('Tested {0} points'.format(len(res.tests)))
    print('Optimal result: num_gangs={0:<6.0f} vector_length={1:<6.0f} => '
            'time {2:.4f}'.format(res.optimal[0], res.optimal[1],
                res.tests[res.optimal]))

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Autotune an OpenACC program')
    parser.add_argument('source', type=str)
    parser.add_argument('-e', '--executable', type=str)
    parser.add_argument('-c', '--compile-command', type=str)
    parser.add_argument('-r', '--repetitions', type=int)
    parser.add_argument('-t', '--time-regexp', type=str)
    #parser.add_argument('--num-gangs-min', type=int)
    #parser.add_argument('--num-gangs-max', type=int)
    #parser.add_argument('--vector-length-min', type=int)
    #parser.add_argument('--vector-length-max', type=int)
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    # Extract provided arguments into a dictionary for easy construction
    # of TuningOptions
    kwargs = dict( (k, args.__dict__[k]) for k in args.__dict__
            if args.__dict__[k] != None )

    t = TuningOptions(**kwargs)

    if args.verbose:
        print('TuningOptions: {0}'.format(t.__dict__))

    tune_scipy(t)


if __name__ == '__main__':
    main()
