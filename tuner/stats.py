import math
import sys

def _avg(ns):
    return sum(ns) / float(len(ns))

def _stdev(ns):
    n = len(ns)
    avg = _avg(ns)
    if n == 1:
        return 0
    else:
        return math.sqrt(sum((x-avg)**2 for x in ns) / float(n-1))

def _t(deg_freedom): # 0.95 quantile of t-variate
    table = [ 6.314, 2.92, 2.353, 2.132, 2.015,
              1.943, 1.895, 1.86, 1.833, 1.812,
              1.796, 1.782, 1.771, 1.761, 1.753,
              1.746, 1.74, 1.734, 1.729, 1.725,
              1.721, 1.717, 1.714, 1.711, 1.708,
              1.706, 1.703, 1.701, 1.699, 1.697 ]
    index = max(int(round(deg_freedom)), 1) - 1
    index = min(index, len(table)-1)
    return table[index]

def is_diff_significant(avg_a, stdev_a, n_a, avg_b, stdev_b, n_b):
    sa2_na = stdev_a**2 / n_a
    sb2_nb = stdev_b**2 / n_b

    mean_diff = avg_a - avg_b
    stdev_mean_diff = math.sqrt(sa2_na + sb2_nb)

    # Compute the number of degrees of freedom
    numerator = (sa2_na + sb2_nb)**2
    denom1 = (1.0 / (n_a+1)) * sa2_na**2
    denom2 = (1.0 / (n_b+1)) * sb2_nb**2
    deg_freedom = numerator / (denom1 + denom2) - 2

    # Compute 90% confidence interval
    low = mean_diff - _t(deg_freedom)*stdev_mean_diff
    high = mean_diff + _t(deg_freedom)*stdev_mean_diff

    # If the confidence interval contains 0, not significantly different
    return not (low <= 0 <= high)
