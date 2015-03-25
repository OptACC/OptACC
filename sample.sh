#!/bin/bash
# Use exhaustive run test data from the test_data directory to count the
# number of benchmark kernels for which the best exhaustive128 result has a
# statistically significant difference from the optimal point in the test data
# (exhaustive32 or exhaustive64).
pass=0
fail=0
for file in `find test_data -iname '*.csv'`; do
	basename=`basename "$file"`
	result=`./tuner.py -s exhaustive128 "$file" 2>&1`
	differs=`echo "$result" | egrep 'DIFFERS|Unable' | cut -c 18-`
	percentile=`echo "$result" | grep ercentile | cut -c 15-`
	if [ "$differs" ]; then
		echo
		echo "$basename: $differs"
		echo "$result" | tail -4 | head -3 | cut -c 15-
		echo
		let fail+=1
	else
		echo "$basename: OK - $percentile"
		let pass+=1
	fi
done
echo
let total=pass+fail
echo "No Significant Difference...........$pass of $total"
echo "Significant Difference or Failure...$fail of $total"
exit 0
