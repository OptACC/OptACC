# Table of Contents

  * [License](#license)
  * [Issue reporting](#issue-reporting)
  * [Getting Started](#getting-started)
    - [Requirements](#requirements)
    - [Installation](#installation)
    - [Running](#running)
    - [Example](#example)
  * [Configuration](#configuration)
    - [Using a different compile command](#using-a-different-compile-command)
    - [Using a different executable](#using-a-different-executable)
    - [Changing the number of repetitions](#changing-the-number-of-repetitions)
    - [Changing the time regexp](#changing-the-time-regexp)
    - [Search methods](#search-methods)
    - [Logging and data reporting](#logging-and-data-reporting)
      - [Output log](#output-log)
      - [CSV output](#csv-output)
      - [gnuplot output](#gnuplot-output)
      - [Excel spreadsheet output](#excel-spreadsheet-output)

# License

Copyright 2015, Auburn University.  All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Issue Reporting

If you discover a bug or other issue with the tuner, please
[open an issue](https://github.com/joverbey/tuner/issues/new) on GitHub.  Please
provide the following information in your description of the issue:

  * Which version of Python are you using? (output of `python -c 'import sys;
    sys.stdout.write(sys.version)'`)
  * Which operating system are you using?
  * Which OpenACC compiler and version are you using?
  * Have you checked that the tuner is fully up to date?
  * Do you have an example program and tuner command that demonstrates the
    issue?

If you get an error message when running the tuner, please report the error
message verbatim (do not paraphrase).  By providing detailed and accurate
information, it will make it easier to determine what is causing your issue.

# Getting Started

## Requirements

The tuner requires Python 2.6 or 2.7.  Python 3.x is currently not supported,
but may be in the future.

## Installation

To install the tuner, simply clone this repository using `git`:

    git clone https://github.com/joverbey/tuner

If you are unable to use `git`, you can also download a
[zip file](https://github.com/joverbey/tuner/archive/master.zip) from GitHub.

## Running

First, navigate to the directory where you cloned the tuner

    cd tuner

To run the tuner, execute `python tuner.py` (or `./tuner.py`).  You can pass the
`-h` flag to produce help information:

```
usage: tuner.py [-h] [-e filename] [-c command] [-a] [-s method] [-r count]
                [-t regexp] [-k] [-l filename.log]
                [--write-gnuplot filename.gp] [--write-csv filename.csv]
                [--write-spreadsheet filename.xml] [--num-gangs-min value]
                [--num-gangs-max value] [--vector-length-min value]
                [--vector-length-max value] [-v] [-x]
                [filename]

Autotune an OpenACC program

positional arguments:
  filename              name of a source file to pass to the compile command

optional arguments:
  -h, --help            show this help message and exit
  -e filename, --executable filename
                        executable to run (default: ./a.out)
  -c command, --compile-command command
                        command line to compile an executable
  -s method, --search-method method
                        search method to use when choosing test points: coord-
                        search, exhaustive-pow2, exhaustive128, exhaustive256,
                        exhaustive32, exhaustive32-vlpow2, exhaustive64,
                        nelder-mead
  -r count, --repetitions count
                        number of times to run the executable to collect
                        timing info
  -t regexp, --time-regexp regexp
                        regular expression to identify timing information in
                        the output produced by the executable
  -k, --kernel-timing   search the output for timing information produced when
                        a program is compiled with "-ta=nvidia,time" using
                        pgcc/pgf90
  -l filename.log, --logfile filename.log
                        write log messages to a file
  --write-gnuplot filename.gp
                        generate a Gnuplot script to visualize the test
                        results
  --write-csv filename.csv
                        write timing results line by line to a CSV file
  --write-spreadsheet filename.xml
                        write an Excel XML spreadsheet with results and
                        statistics
  --num-gangs-min value
                        minimum allowable value of num_gangs
  --num-gangs-max value
                        maximum allowable value of num_gangs
  --vector-length-min value
                        minimum allowable value of vector_length
  --vector-length-max value
                        maximum allowable value of vector_length
  -v, --verbose         display progress and diagnostic information while
                        tuning
  -x, --ignore-exit     continue with autotuning even if the executable exits
                        with a nonzero exit code
```

## Example

Suppose we wish to tune the following code:

```c
    #include <stdio.h>
    #define N 16772240
    int main() {
        static double a[N];
        #pragma acc parallel loop
        for (int i = 0; i < N; i++) {
            a[i] = i;
        }

        return 0;
    }
```

First, we must add `num_gangs` and `vector_length` clauses to the `parallel
loop` directive, so that we can tune these parameters.  We must also add time
measurement to report the runtime of the kernel.  In this example, we will use
the `omp_get_wtime()` timer provided by OpenMP.

```c
    #include <stdio.h>
    #include <omp.h>
    #define N 16772240
    int main() {
        static double a[N];
        double start = omp_get_wtime();
        #pragma acc parallel loop num_gangs(NUM_GANGS) vector_length(VECTOR_LENGTH)
        for (int i = 0; i < N; i++) {
            a[i] = i;
        }
        double end = omp_get_wtime();

        printf("time: %f\n", end - start);
        return 0;
    }
```

Note that the format of the printed time must follow a specific format (this
format can be configured; see
[Changing the time regexp](#changing-the-time-regexp)).
By default, times of the form `time: %f` and `time=%f` are recognized.

Now we are ready to tune our kernel.  We invoke the tuner, providing our file,
`example.c` as input:

    python tuner.py example.c

The output should look something like this:

    11:31:55 INFO   [num_gangs: 256, vector_length: 128] Average: 0.989616, Standard Deviation: 0.004065
    11:32:14 INFO   [num_gangs: 224, vector_length:  64] Average: 0.990643, Standard Deviation: 0.005504
    11:32:33 INFO   [num_gangs: 224, vector_length: 128] Average: 0.989230, Standard Deviation: 0.001565
    11:32:52 INFO   [num_gangs: 256, vector_length: 256] Average: 0.992265, Standard Deviation: 0.006641
    11:32:52 INFO   -- RESULTS --
    11:32:52 INFO   num_gangs=256  vector_length=256  => time=0.992265 (stdev=0.00664067180336)
    11:32:52 INFO   num_gangs=224  vector_length=64   => time=0.9906433 (stdev=0.00550409968518)
    11:32:52 INFO   num_gangs=256  vector_length=128  => time=0.9896164 (stdev=0.00406480567255)
    11:32:52 INFO   num_gangs=224  vector_length=128  => time=0.9892305 (stdev=0.00156527997141)
    11:32:52 INFO   -------------
    11:32:52 INFO   Tested 4 points
    11:32:52 INFO   Search took 2 iterations
    11:32:52 INFO   Best result found: num_gangs=224  vector_length=128  => time=0.9892305 (stdev=0.00156527997141)


The tuner will log informational message as it progresses, as well as errors if
any are encountered.  At the end, the results of tuning will be displayed.  If
you would like to see extra information about what actions the tuner is taking,
pass the `-v` flag on the command line to enable verbose mode.

By default the tuner invokes the PGI compiler to compile the source file and
executes `./a.out` to run the program.  You can change these with command line
flags (see
[Using a different compile command](#using-a-different-compile-command),
[Using a different executable](#using-a-different-executable)).

# Configuration

## Using a different compile command

By default, the tuner uses the following command to compile:

    pgcc -acc -DNUM_GANGS={num_gangs} -DVECTOR_LENGTH={vector_length} {source}

If you are using a different compiler, or if you need to pass specific flags to
pgcc, then you will need to change the compile command by using the `-c` flag.
Within the compile command string, the following format specifiers will be
substituted when the program is compiled:

  * `{num_gangs}`: the current value for num\_gangs being tested
  * `{vector_length}`: the current value for vector\_length being tested
  * `{source}` the source file passed to the tuner

In addition, values for num\_gangs and vector\_length are stored in the
environment variables `NUM_GANGS` and `VECTOR_LENGTH` when the compile command
is executed, allowing you to use these values in Makefiles.

Examples:

    python tuner.py -c 'pgcc -acc -DNUM_GANGS={num_gangs} -DVECTOR_LENGTH={vector_length} -D_MG_OACC {source}' example.c
    python tuner.py -c 'make'

## Using a different executable

By default, the tuner executes `./a.out` to run the program (this is what is
produced when the default compile command is run).  If your executable has a
different name, use the `-e` flag to tell the tuner to run this executable
instead.

Example:

    python tuner.py -e './my-application' -c 'make'

## Changing the number of repetitions

In order to improve the accuracy of the timing data used to tune the program,
the program is invoked multiple times for each set of parameters and the
resulting times are used to calculate the average time and standard deviation.
By default, the number of repetitions is 10.  However, for programs that take a
long time to run, it may be desirable to use less repetitions, by passing the
`-r` flag.

Example:

    python tuner.py -r 3 example.c # Tune example.c using 3 repetitions

## Changing the time regexp

The runtime of the kernel is reported from within the program itself (rather
than measuring the runtime of the entire program), hence the tuner needs to
match the time output from the program.  By default, the following formats will
be recognized:

    time: 0.123
    time=0.123

Spaces after the colon or equals sign are ignored, and capitalization does not
matter.  If you wish to report the timing data using some other format, you will
need to use the `-t` flag to provide a Python style regular expression that
matches your time output and groups the decimal number representing the time.

For example, to match the output:

    time in seconds - 0.123

Use the following command:

    python tuner.py -t 'time in seconds - ([\d.]+)' example.c

The Python documentation for the
[re](https://docs.python.org/2.6/library/re.html) module describes the regular
expression syntax.

## Search methods

The tuner supports several different search methods.  The default search method
is `nelder-mead`.  The following table lists the available search methods:

Name  | Description  | # Points Tested
----- | ------------ | ---------------
nelder-mead | Nelder-Mead direct search method | 7 (average)
coord-search | Coordinate search (another direct search method) | 11 (average)
exhaustive32 | Exhaustively try every multiple of 32 | 1024
exhaustive64 | Exhaustively try every multiple of 64 | 256
exhaustive128 | Exhaustively try every multiple of 128 | 64
exhaustive-pow2 | Exhaustively try every power of 2 | 100
exhaustive32-vlpow2 | Exhaustively try multiples of 32 for num\_gangs and powers of 2 for vector\_length | 320

Methods beginning with `exhaustive` are exhaustive methods-- they test all
points on certain intervals with no heuristic.  `nelder-mead` and `coord-search`
are direct search algorithms aimed at finding locally optimal values while
testing relatively few points.

Examples:

    python tuner.py -s exhaustive32 example.c
    python tuner.py -s coord-search example.c

## Logging and data reporting

In addition to printing results to the console, the tuner can save various
information to files.

### Output log

When the `-l` flag is provided, console output will also be logged to a file.

Example:

    python tuner.py -l example.log example.c

### CSV output

When the `--write-csv` flag is provided, the tuner will write results for each
point tested to a CSV file as they are tested.  This may be useful for
extracting partial data if tuning fails.

Example:

    python tuner.py --write-csv example.csv example.c

Example output (example.csv):

    num_gangs,vector_length,time,stdev,error msg
    256,128,0.9896163999999998,0.004064805672545197
    224,64,0.9906433,0.0055040996851841795
    224,128,0.9892304999999999,0.0015652799714073243
    256,256,0.992265,0.006640671803364472
    ...

### gnuplot output

When the `--write-gnuplot` flag is provided, the tuner will write 2 files: a
`.dat` file containing tuning data, and a `.gp` file containing a gnuplot script
to render the contents of the data file into 3D surfaces.  Note that the
generated script uses the `pm3d` plot style, which is only available since
gnuplot 5.0.

Example:

    python tuner.py --write-gnuplot example.gp example.c

Example output (example.dat):

    224    64     0.9906433 0.00550409968518
    224    128    0.9892305 0.00156527997141

    256    128    0.9896164 0.00406480567255
    256    256    0.992265 0.00664067180336
    ...

Example output (example.gp):

    # Script for gnuplot 5.0
    set term postscript eps enhanced color size 10, 21 "Times-Roman,24"
    set output "example.eps"
    set multiplot layout 3,1

    set title "All Points Tested - Optimal: 224 gangs, vector length 128 - Resulting time 0.9892305 (stdev: 0.00156527997141)"
    set xlabel "Num Gangs"
    set ylabel "Vector Length"
    set zlabel "Time" rotate
    set label 1 "0.9892305" at 224.0, 128.0, 0.9892305 left
    ...

### Excel spreadsheet output

When the `--write-spreadsheet` flag is provided, the tuner will write an XML
file for use with Microsoft Excel.  This file contains the results of tuning
as well as a formula for determining whether the speedup is statistically
significant, given the average time and standard deviation of the untuned
program.

Example:

    python tuner.py --write-spreadsheet example.xml example.c
