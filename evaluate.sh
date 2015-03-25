#!/bin/bash
# Use exhaustive run test data from the test_data directory to count the number
# of benchmark kernels for which a search method (default: Nelder-Mead)
# produces a result that is (1) statistically significantly different from the
# optimal point in the test data (exhaustive32 or exhaustive64) and (2) not in
# the top 5% of test points.

# Usage: ./evaluate.sh [search-method]

if [ "$1" == "" ]; then
	method=nelder-mead
else
	method="$1"
fi

echo "Evaluating $method..."
echo
pass=0
fail=0
for file in `find test_data -iname '*.csv'`; do
	basename=`basename "$file"`
	result=`./tuner.py -s "$method" "$file" 2>&1`
	if [ $? -ne 0 ]; then
		echo "$result"
		exit 1
	fi
	differs=`echo "$result" | egrep 'DIFFERS|Unable' | cut -c 18-`
	percentile=`echo "$result" | grep ercentile | cut -c 42- | cut -f 1 -d '%'`
	if [ "$differs" ]; then
		if [ "$percentile" -gt 5 ]; then
			echo "$basename: DIFFERS - Result in top $percentile%"
			let fail+=1
		else
			#echo "$basename: OK - $percentile%"
			let pass+=1
		fi
	else
		#echo "$basename: OK - $percentile%"
		let pass+=1
	fi
done
echo
let total=pass+fail
echo "No Significant Difference...........$pass of $total"
echo "Significant Difference or Failure...$fail of $total"
exit 0
