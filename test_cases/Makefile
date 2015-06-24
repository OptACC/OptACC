# Run "make test" to run OptACC with all of its various command line options
# and search methods.  This is not a complete test suite but rather is intended
# for sanity checking.

# Path to the python interpreter (change to customize)
PYTHON=python

all:
	@echo "Run 'make test' to run a suite of tests for OptACC."
	@echo "The tests assume pgcc is on the PATH."

test: \
	test_basic \
	test_compilefail \
	test_nonzero \
	test_nonzero_ok \
	test_notime \
	test_kernel_timing \
	test_custom \
	test_fromfile \
	test_methods \
	test_output

test_basic:
	@echo "$(tput setaf 1)Testing simple.c, default search method, -r 3$(tput sgr 0)"
	$(PYTHON) ../tuner.py -v -r 3 simple.c

test_compilefail:
	@echo "$(tput setaf 1)Testing simple-compilefail.c (should fail)$(tput sgr 0)"
	$(PYTHON) ../tuner.py -v -r 3 simple-compilefail.c | grep 'error=Compile command failed'

test_nonzero:
	@echo "$(tput setaf 1)Testing simple-nonzero.c (should fail)$(tput sgr 0)"
	$(PYTHON) ../tuner.py -v -r 3 simple-nonzero.c | grep 'error=Executable failed'

test_nonzero_ok:
	@echo "$(tput setaf 1)Testing simple-nonzero.c with -x$(tput sgr 0)"
	$(PYTHON) ../tuner.py -v -x -r 3 simple-nonzero.c

test_notime:
	@echo "$(tput setaf 1)Testing simple-notime.c (should fail)$(tput sgr 0)"
	$(PYTHON) ../tuner.py -v -r 3 simple-notime.c | grep 'error=Timing data missing'

test_kernel_timing:
	@echo "$(tput setaf 1)Testing simple-notime.c with kernel timing$(tput sgr 0)"
	$(PYTHON) ../tuner.py -v -k -r 3 simple-notime.c

test_custom:
	@echo "$(tput setaf 1)Testing custom compilation command and executable$(tput sgr 0)"
	$(PYTHON) ../tuner.py \
		--num-gangs-min 32 --num-gangs-max 32 \
		--vector-length-min 32 --vector-length-max 32 \
		-s grid32 -v -r 1 \
		-c 'gcc -fopenmp -std=c99 -o custom.out -DNUM_GANGS={num_gangs} -DVECTOR_LENGTH={vector_length} -D_MG_OACC {source}' \
		-e ./custom.out \
		simple.c ; rm -f custom.out

test_fromfile:
	@echo "$(tput setaf 1)Testing simple.c, saving and loading CSV file$(tput sgr 0)"
	rm -f simple.csv
	$(PYTHON) ../tuner.py \
		--num-gangs-min 32 --num-gangs-max 128 \
		--vector-length-min 32 --vector-length-max 128 \
		-s grid32 -v -r 2 \
		--write-csv simple.csv \
		simple.c
	$(PYTHON) ../tuner.py \
		--num-gangs-min 32 --num-gangs-max 128 \
		--vector-length-min 32 --vector-length-max 128 \
		-s coord-search -v \
		simple.csv

test_methods:
	for method in coord-search grid-pow2 grid128 grid256 grid32 grid32-vlpow2 grid64 nelder-mead; \
	do \
		$(PYTHON) ../tuner.py \
			--num-gangs-min 256 --num-gangs-max 512 \
			--vector-length-min 256 --vector-length-max 512 \
			-s $$method -v -r 1 \
			simple.c;
	done

test_output:
	@echo "$(tput setaf 1)Testing output files$(tput sgr 0)"
	rm -f simple*.{gp,dat,xml,log}
	for file in simple simple-nonzero; do \
		$(PYTHON) ../tuner.py \
			--num-gangs-min 32 --num-gangs-max 128 \
			--vector-length-min 32 --vector-length-max 128 \
			-s grid32 -v -r 2 \
			-l $$file.log \
			--write-gnuplot $$file.gp \
			--write-spreadsheet $$file.xml \
			simple.c; \
	done
	$(PYTHON) ../tuner.py \
		--num-gangs-min 32 --num-gangs-max 128 \
		--vector-length-min 32 --vector-length-max 128 \
		-s grid32 -v -r 1 \
		-l simple-nostdev.log \
		--write-gnuplot simple-nostdev.gp \
		--write-spreadsheet simple-nostdev.xml \
	@echo "$(tput setaf 1)Please manually check the .gp and .xml output files.$(tput sgr 0)"
