#!/usr/bin/env python3
import math

def parse_benchmarks(report_file):
    """
    Parse the benchmark report file and calculate relative performance.
    """
    results = []

    with open(report_file, 'r') as f:
        # Skip the header line
        next(f)

        for line in f:
            parts = line.strip().split()
            if len(parts) >= 4:
                benchmark = parts[0]
                try:
                    native_val = float(parts[1])
                    aot_val = float(parts[2])
                    aot_pgo_val = float(parts[3])

                    # Calculate percentages (higher means slower)
                    if native_val > 0:
                        aot_percent = (aot_val / native_val)
                        aot_pgo_percent = (aot_pgo_val / native_val)
                        # Calculate speedup of PGO over non-PGO AOT (value > 1 means PGO is faster)
                        pgo_speedup = aot_val / aot_pgo_val if aot_pgo_val > 0 else float('nan')
                        results.append((benchmark, aot_percent, aot_pgo_percent, pgo_speedup))
                    else:
                        # Handle division by zero
                        results.append((benchmark, float('nan'), float('nan'), float('nan')))
                except ValueError:
                    # Skip lines with invalid number format
                    continue

    return results

def main():
    report_file = "report.txt"
    results = parse_benchmarks(report_file)

    # Print the results
    print(f"{'Benchmark':<30} {'iwasm-aot/native':<20} {'iwasm-aot-pgo/native':<20} {'PGO speedup':<15}")
    print("-" * 85)

    for benchmark, aot_percent, aot_pgo_percent, pgo_speedup in results:
        print(f"{benchmark:<30} {aot_percent:>18.2f} {aot_pgo_percent:>18.2f} {pgo_speedup:>13.2f}x")

    # Calculate statistics for PGO speedup
    speedups = [s for _, _, _, s in results if isinstance(s, float) and not math.isnan(s)]

    if speedups:
        # Sort for calculating median
        speedups.sort()

        # Calculate median
        if len(speedups) % 2 == 0:
            median = (speedups[len(speedups)//2 - 1] + speedups[len(speedups)//2]) / 2
        else:
            median = speedups[len(speedups)//2]

        # Calculate variance
        mean = sum(speedups) / len(speedups)
        variance = sum((x - mean) ** 2 for x in speedups) / len(speedups)

        # Print statistics
        print("\nPGO Speedup Statistics:")
        print(f"Maximum: {max(speedups):.2f}x")
        print(f"Minimum: {min(speedups):.2f}x")
        print(f"Median:  {median:.2f}x")
        print(f"Variance: {variance:.4f}")
    else:
        print("\nNo valid PGO speedup values available for statistics.")

if __name__ == "__main__":
    main()
