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
total_points=0
max_points_per_kernel=0
for file in `find test_data -iname '*.csv'`; do
	basename=`basename "$file"`
	result=`./tuner.py -s "$method" "$file" 2>&1`
	if [ $? -ne 0 ]; then
		echo "$result"
		exit 1
	fi
	points=`echo "$result" | grep Tested | cut -c 22-`
	differs=`echo "$result" | egrep 'DIFFERS|Unable' | cut -c 18-`
	percentile=`echo "$result" | grep ercentile | cut -c 42- | cut -f 1 -d '%'`
	if [ "$differs" ]; then
		if [ "$percentile" -gt 5 ]; then
			echo "$basename: DIFFERS - Result in top $percentile%"
			let fail+=1
		else
			#echo "$basename: OK - $percentile% - $points"
			let pass+=1
		fi
	else
		#echo "$basename: OK - $percentile% - $points"
		let pass+=1
	fi

	let add=`echo "$points" | sed -e 's/ points//'`
	if [ "$add" -gt "$max_points_per_kernel" ]; then
		let max_points_per_kernel=add
	fi
	let total_points+=$add
done
echo
let total_tests=pass+fail
let avg=total_points/total_tests
echo "$total_points points tested in total; average: $avg per kernel (max: $max_points_per_kernel)"
echo "No Significant Difference or Top 5%...$pass of $total_tests"
echo "Significant Difference or Failure.....$fail of $total_tests"
exit 0
