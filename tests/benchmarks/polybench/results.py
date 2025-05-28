import os
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Directory to save plots
PLOTS_DIR = Path("results/plots")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Update the data loading function to reflect the correct CSV columns
def load_data():
    report_file = Path("./report.csv")
    if not report_file.exists():
        print("Error: report.csv not found.")
        return pd.DataFrame()

    try:
        return pd.read_csv(report_file, names=["benchmark_name","native_min","native_max","native_median","native_stddev","aot_min","aot_max","aot_median","aot_stddev","aot_pgo_min","aot_pgo_max","aot_pgo_median","aot_pgo_stddev"], header=0)
    except Exception as e:
        print(f"Error reading report.csv: {e}")
        return pd.DataFrame()

# Create individual bar charts for each benchmark
def create_individual_charts(df):
    for _, row in df.iterrows():
        benchmark = row["benchmark_name"]
        times = row[["native_median", "aot_median", "aot_pgo_median"]].astype(float)

        plt.figure(figsize=(8, 6))
        plt.bar(["Native", "AOT", "PGO AOT"], times, color=["blue", "orange", "green"])
        plt.title(f"Execution Times for {benchmark}")
        plt.ylabel("Time (s)")
        print(f"Creating plot for {benchmark}...")
        plt.savefig(PLOTS_DIR / f"{benchmark}.svg", format="svg")
        plt.close()

# Update the normalized bar chart to group columns into three distinct groups with three colors and legend entries
def create_normalized_chart(df):
    normalized_df = df.copy()
    normalized_df[["aot_median", "aot_pgo_median"]] = normalized_df[["aot_median", "aot_pgo_median"]].div(normalized_df["native_median"], axis=0)
    normalized_df["native_median"] = 1.0  # Native execution is the baseline

    plt.figure(figsize=(12, 8))

    # Prepare data for grouped bar chart
    benchmarks = normalized_df["benchmark_name"]
    native_times = normalized_df["native_median"]
    aot_times = normalized_df["aot_median"]
    pgo_aot_times = normalized_df["aot_pgo_median"]

    x = range(len(benchmarks))  # X-axis positions for benchmarks

    bar_width = 0.25  # Width of each bar

    # Plot each group of bars
    plt.bar(x, native_times, width=bar_width, label="Native", color="blue")
    plt.bar([pos + bar_width for pos in x], aot_times, width=bar_width, label="AOT", color="orange")
    plt.bar([pos + 2 * bar_width for pos in x], pgo_aot_times, width=bar_width, label="PGO AOT", color="green")

    # Add labels and legend
    plt.xticks([pos + bar_width for pos in x], benchmarks, rotation=90)
    plt.title("Normalized Execution Times (Relative to Native)")
    plt.ylabel("Normalized Time")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "normalized_execution_times.svg", format="svg")
    plt.close()

# Main function
def main():
    df = load_data()
    if df.empty:
        print("No data found in partial reports.")
        return

    create_individual_charts(df)
    create_normalized_chart(df)

if __name__ == "__main__":
    main()
