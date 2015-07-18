import re

# Default compilation command
PGCC_COMPILE = ('pgcc -acc -ta=nvidia -DNUM_GANGS={num_gangs} '
                '-DVECTOR_LENGTH={vector_length} {source}')
PGCC_COMPILE_KERNEL_TIMING = ('pgcc -acc -DNUM_GANGS={num_gangs} '
                '-DVECTOR_LENGTH={vector_length} -ta=nvidia,time {source}')

# Default regular expression matching the time output
TIME_RE = r'(?:time)[=:\s]*([\d.]+)'

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
