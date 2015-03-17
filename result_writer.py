import csv

from collections import namedtuple

ResultFiles = namedtuple('ResultFiles', ['gnuplot', 'csv'])

class ResultWriter(object):
    '''Utility class for writing output data from the tuning process.'''

    def __init__(self, data_files):
        self.data_files = data_files
        self.csv_file = None

    def __enter__(self):
        if self.data_files.csv:
            self.csv_file = open(self.data_files.csv, 'wb')
            self.csv_writer = csv.writer(self.csv_file, delimiter=',',
                quotechar='"', quoting=csv.QUOTE_MINIMAL)
            self.csv_writer.writerow(['num_gangs', 'vector_length', 'time',
                'stdev', 'error'])
        return self

    def _add_row_to_csv(self, test_result):
        row = [ '{0:.0f}'.format(test_result.point[0]),
                '{0:.0f}'.format(test_result.point[1]),
                test_result.average,
                test_result.stdev ]
        if test_result.error:
            row.append(test_result.error)
        self.csv_writer.writerow(row)

    def add(self, test_result):
        if self.csv_file:
            self._add_row_to_csv(test_result)

    def _write_gnuplot_output(self, search_result):
        with open(self.data_files.gnuplot + '.dat', 'w') as f:
            lastx = 0
            for point in sorted(search_result.tests, key=lambda pt: pt.coords):
                res = search_result.tests[point]
                if res.has_error:
                    continue
                if point[0] != lastx:
                    f.write('\n') # Blank line between successive x-values
                    lastx = point[0]
                f.write('{0:<6.0f} {1:<6.0f} {2} {3}\n'.format(
                    point[0], point[1], res.average, res.stdev))

        with open(self.data_files.gnuplot + '.gp', 'w') as f:
            fmt = """# Script for gnuplot 5.0
set term postscript eps enhanced color size 10, 21 "Times-Roman,24"
set output "{0}.eps"
set multiplot layout 3,1

set title "All Points Tested - Optimal: {1:.0f} gangs, vector length {2:.0f} - Resulting time {3} (stdev: {4})"
set xlabel "Num Gangs"
set ylabel "Vector Length"
set zlabel "Time" rotate
set label 1 "{3}" at {1}, {2}, {3} left
set grid

splot '{0}.dat' using 1:2:3 notitle with points pointtype 7

splot '{0}.dat' using 1:2:3 notitle with linespoints

set pm3d border linetype -1 linewidth 0.5
set palette
set hidden3d
splot '{0}.dat' using 1:2:3 notitle pal with pm3d
"""
            optimal = search_result.optimal
            f.write(fmt.format(
                self.data_files.gnuplot,
                optimal[0],
                optimal[1],
                search_result.tests[optimal].average,
                search_result.tests[optimal].stdev))

    def write_result(self, search_result):
        if self.data_files.gnuplot is not None:
            self._write_gnuplot_output(search_result)

    def __exit__(self, type, value, traceback):
        if self.csv_file is not None:
            self.csv_file.close()
