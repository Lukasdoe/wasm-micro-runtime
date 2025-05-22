#!/usr/bin/env python3

# Copyright (C) 2019 Intel Corporation.  All rights reserved.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Python conversion of the original test_pgo.sh script.

import os
import sys
import shutil
import subprocess
import argparse
import tempfile
from pathlib import Path
import platform as pf_platform # Renamed to avoid conflict with PLATFORM variable
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
import dataclasses
from typing import List, Union

# --- Configuration Constants ---
BENCH_NAME_MAX_LEN = 20
MAX_JOBS = 10

POLYBENCH_CASES_STR = ("2mm 3mm adi atax bicg cholesky correlation covariance "
                       "deriche doitgen durbin fdtd-2d floyd-warshall gemm gemver "
                       "gesummv gramschmidt heat-3d jacobi-1d jacobi-2d ludcmp lu "
                       "mvt nussinov seidel-2d symm syr2k syrk trisolv trmm")

# --- Helper Functions ---

def run_command(cmd_list: List[Union[str, Path]], cwd: Path = None, check: bool = True, capture_output: bool = False, shell: bool = False):
    """Runs a shell command."""
    cmd_str_list = [str(c) for c in cmd_list]
    print(f"Executing: {' '.join(cmd_str_list)}{' (in ' + str(cwd) + ')' if cwd else ''}")
    try:
        process = subprocess.run(cmd_str_list, cwd=cwd, check=check, text=True,
                                 capture_output=capture_output, shell=shell)
        return process
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd_str_list)}\n{e}", file=sys.stderr)
        if e.stdout: print(f"STDOUT:\n{e.stdout}", file=sys.stderr)
        if e.stderr: print(f"STDERR:\n{e.stderr}", file=sys.stderr)
        if check:
            raise
        return e # Return error object if check is False
    except FileNotFoundError as e:
        print(f"Error: Command not found: {cmd_str_list[0]} - {e}", file=sys.stderr)
        raise

# --- Dataclass for Configuration ---
@dataclasses.dataclass
class ScriptConfig:
    sgx_mode: bool
    workspace_root: Path
    script_dir: Path
    out_dir: Path
    report_file: Path
    iwasm_cmd: Path
    wamrc_cmd: Path
    llvm_profdata_cmd: Path
    polybench_cases: List[str]
    bench_name_max_len: int = BENCH_NAME_MAX_LEN
    max_jobs: int = MAX_JOBS

def setup_config(args: argparse.Namespace) -> ScriptConfig:
    """Sets up paths and commands based on arguments and environment."""
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent.parent.parent # Assuming tests/benchmarks/polybench structure

    out_dir = script_dir / "out"
    report_file = script_dir / "report.csv" # Changed from report.txt

    platform_name = pf_platform.system().lower()

    iwasm_cmd_path_str = f"../../../product-mini/platforms/{platform_name}/build/iwasm"
    wamrc_cmd_path_str = "../../../wamr-compiler/build/wamrc"

    if args.sgx and platform_name == "linux":
        iwasm_cmd_path_str = f"../../../product-mini/platforms/{platform_name}-sgx/enclave-sample/iwasm"
        wamrc_cmd_path_str = "../../../wamr-compiler/build/wamrc -sgx" # Note: command with arg

    iwasm_cmd = (script_dir / iwasm_cmd_path_str).resolve()

    wamrc_base_cmd = (script_dir / "../../../wamr-compiler/build/wamrc").resolve()
    wamrc_cmd_list = [wamrc_base_cmd]
    if args.sgx and platform_name == "linux":
        wamrc_cmd_list.append("-sgx")

    llvm_profdata_cmd = (workspace_root / "core/deps/llvm/build/bin/llvm-profdata").resolve()

    return ScriptConfig(
        sgx_mode=args.sgx,
        workspace_root=workspace_root,
        script_dir=script_dir,
        out_dir=out_dir,
        report_file=report_file,
        iwasm_cmd=iwasm_cmd,
        wamrc_cmd=wamrc_base_cmd, # Store base command, options added separately
        llvm_profdata_cmd=llvm_profdata_cmd,
        polybench_cases=POLYBENCH_CASES_STR.split()
    )

# --- Core Logic Functions ---

def compile_and_profile_one(config: ScriptConfig, case_name: str):
    """Performs compilation and profile generation for a single benchmark case."""
    print(f"\n--- Processing case: {case_name} ---")

    wasm_file = config.out_dir / f"{case_name}.wasm"
    if not wasm_file.exists():
        print(f"Error: {wasm_file.name} doesn't exist, please run build.sh first (or ensure it's generated).", file=sys.stderr)
        return

    wamrc_base_cmd_list = [config.wamrc_cmd]
    if config.sgx_mode and pf_platform.system().lower() == "linux":
        wamrc_base_cmd_list.append("-sgx")

    aot_file = config.out_dir / f"{case_name}.aot"
    if not aot_file.exists():
        print(f"\nCompile {wasm_file.name} to {aot_file.name} ..")
        cmd = wamrc_base_cmd_list + ["-o", str(aot_file.name), str(wasm_file.name)]
        run_command(cmd, cwd=config.out_dir)
    else:
        print(f"\n{aot_file.name} already exists, skipping.")

    pgo_aot_file = config.out_dir / f"{case_name}_pgo.aot"
    if not pgo_aot_file.exists():
        print(f"\nCompile {wasm_file.name} to {pgo_aot_file.name} ..")
        cmd = wamrc_base_cmd_list + ["--enable-llvm-pgo", "-o", str(pgo_aot_file.name), str(wasm_file.name)]
        run_command(cmd, cwd=config.out_dir)
    else:
        print(f"\n{pgo_aot_file.name} already exists, skipping.")

    profdata_file = config.out_dir / f"{case_name}.profdata"
    profraw_file = config.out_dir / f"{case_name}.profraw"

    if not profdata_file.exists():
        print("")
        if pgo_aot_file.exists():
            print(f"Run {pgo_aot_file.name} to generate the raw profile data ({profraw_file.name}) ..")
            run_command([config.iwasm_cmd, f"--gen-prof-file={profraw_file.name}", "--dir=.", str(pgo_aot_file.name)], cwd=config.out_dir)

            if profraw_file.exists():
                print(f"Merge the raw profile data to {profdata_file.name} ..")
                if profdata_file.exists():
                    profdata_file.unlink()

                merge_cmd = [config.llvm_profdata_cmd, "merge", f"-output={profdata_file.name}", str(profraw_file.name)]
                try:
                    run_command(merge_cmd, cwd=config.out_dir)
                    if not profdata_file.exists():
                        print(f"Warning: Merge command for {profdata_file.name} seemed to succeed but file is missing.", file=sys.stderr)
                except subprocess.CalledProcessError:
                    print(f"Error: Failed to create {profdata_file.name} from {profraw_file.name}.", file=sys.stderr)
            else:
                print(f"Error: {profraw_file.name} not generated. Cannot create {profdata_file.name} for {case_name}.", file=sys.stderr)
        else:
            print(f"Error: {pgo_aot_file.name} not found. Cannot generate profile data for {case_name}.", file=sys.stderr)
    else:
        print(f"\n{profdata_file.name} already exists, skipping profile generation.")

    opt_aot_file = config.out_dir / f"{case_name}_opt.aot"
    if not opt_aot_file.exists():
        print("")
        if profdata_file.exists():
            print(f"Compile {wasm_file.name} to {opt_aot_file.name} with the profile data ..")
            cmd = wamrc_base_cmd_list + [f"--use-prof-file={profdata_file.name}", "-o", str(opt_aot_file.name), str(wasm_file.name)]
            run_command(cmd, cwd=config.out_dir)
        else:
            print(f"Error: {profdata_file.name} not found. Cannot compile {opt_aot_file.name} for {case_name}.", file=sys.stderr)
    else:
        print(f"\n{opt_aot_file.name} already exists, skipping.")


def run_hyperfine_for_case(config: ScriptConfig, case_name: str, partial_report_dir: Path) -> str:
    """Runs hyperfine for a single benchmark case and writes results to a partial CSV report file."""
    report_part_file = partial_report_dir / f"{case_name}.part" # Partial file, content is CSV

    cmd_native = f"./{case_name}_native"
    cmd_aot = f"{config.iwasm_cmd} {case_name}.aot"
    cmd_aot_opt = f"{config.iwasm_cmd} {case_name}_opt.aot"

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv", dir=config.out_dir) as tmp_csv_file:
        hyperfine_csv_path = Path(tmp_csv_file.name)

    print(f"Benchmarking {case_name} with hyperfine (native, WAMR AOT, WAMR AOT+PGO) ..")
    hyperfine_cmd = [
        "hyperfine", "--ignore-failure", "--warmup", "1", "--runs", "2",
        "--export-csv", str(hyperfine_csv_path),
        cmd_native,
        cmd_aot,
        cmd_aot_opt
    ]
    run_command(hyperfine_cmd, cwd=config.out_dir, capture_output=True)

    means = []
    expected_means_count = 3
    if hyperfine_csv_path.exists() and hyperfine_csv_path.stat().st_size > 0:
        try:
            with open(hyperfine_csv_path, 'r', newline='') as f_csv:
                reader = csv.DictReader(f_csv)
                for row in reader:
                    means.append(row['mean'])
            if len(means) != expected_means_count:
                print(f"Warning: Expected {expected_means_count} mean values from hyperfine for {case_name}, got {len(means)}. Using ERROR placeholders.", file=sys.stderr)
                means = ["ERROR_DATA_COUNT"] * expected_means_count
        except Exception as e_csv:
            print(f"Warning: Error reading hyperfine CSV for {case_name}: {e_csv}. Using ERROR placeholders.", file=sys.stderr)
            means = ["ERROR_CSV_READ"] * expected_means_count
        finally:
            if hyperfine_csv_path.exists():
                hyperfine_csv_path.unlink()
    else:
        print(f"Warning: Hyperfine CSV for {case_name} not found or empty. Using ERROR placeholders.", file=sys.stderr)
        if hyperfine_csv_path.exists():
            hyperfine_csv_path.unlink()
        means = ["ERROR_HYPERFINE_CSV"] * expected_means_count

    csv_row_data = [case_name] + means

    with open(report_part_file, "w", newline='') as f_part_csv:
        writer = csv.writer(f_part_csv)
        writer.writerow(csv_row_data)

    return case_name


# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Python version of test_pgo.sh for Polybench benchmarks.")
    parser.add_argument("--sgx", action="store_true", help="Enable SGX mode (relevant for Linux).")
    args = parser.parse_args()

    config = setup_config(args)

    config.out_dir.mkdir(parents=True, exist_ok=True)

    if config.report_file.exists():
        config.report_file.unlink()

    csv_header = ["benchmark_name", "native_time", "aot_time", "aot_pgo_time"]
    with open(config.report_file, "w", newline='') as rf_csv:
        writer = csv.writer(rf_csv)
        writer.writerow(csv_header)

    current_original_dir = Path.cwd()

    print("--- Starting Compilation and Profiling Phase ---")
    for case_name in config.polybench_cases:
        compile_and_profile_one(config, case_name)
    print("--- Compilation and Profiling Phase Finished ---")

    print("\nStart to run cases, the result is written to report.csv")

    with tempfile.TemporaryDirectory(prefix="poly_bench_parts_", dir=config.script_dir) as tmp_partial_dir_str:
        partial_report_dir = Path(tmp_partial_dir_str)
        print(f"Partial reports will be stored in: {partial_report_dir}")

        futures = {}
        with ProcessPoolExecutor(max_workers=config.max_jobs) as executor:
            for case_name in config.polybench_cases:
                future = executor.submit(run_hyperfine_for_case, config, case_name, partial_report_dir)
                futures[future] = case_name

        for future in as_completed(futures):
            case_name = futures[future]
            try:
                result = future.result()
                print(f"Finished benchmarking for: {result}")
            except Exception as e:
                print(f"Error benchmarking {case_name}: {e}", file=sys.stderr)
                error_part_file = partial_report_dir / f"{case_name}.part"
                if not error_part_file.exists():
                    error_csv_data = [case_name, "ERROR", "ERROR", "ERROR"]
                    with open(error_part_file, "w", newline='') as f_err_csv:
                        writer = csv.writer(f_err_csv)
                        writer.writerow(error_csv_data)

        print(f"\nAggregating results into {config.report_file} ...")
        all_results_data = []

        for case_name_iter in config.polybench_cases:
            part_file = partial_report_dir / f"{case_name_iter}.part"
            if part_file.exists() and part_file.is_file():
                try:
                    with open(part_file, 'r', newline='') as f_part_csv:
                        reader = csv.reader(f_part_csv)
                        data_row = next(reader)
                        if data_row and len(data_row) == 4 and data_row[0] == case_name_iter:
                            all_results_data.append(data_row)
                        else:
                            print(f"Warning: Malformed partial report for {case_name_iter}. Using NA.", file=sys.stderr)
                            all_results_data.append([case_name_iter, "NA", "NA", "NA"])
                except StopIteration:
                    print(f"Warning: Empty partial report for {case_name_iter}. Using NA.", file=sys.stderr)
                    all_results_data.append([case_name_iter, "NA", "NA", "NA"])
                except Exception as ex_read:
                    print(f"Warning: Could not read or parse partial report for {case_name_iter}: {ex_read}. Using NA.", file=sys.stderr)
                    all_results_data.append([case_name_iter, "NA", "NA", "NA"])
            else:
                print(f"Warning: Partial report for {case_name_iter} not found. Using NA values.", file=sys.stderr)
                all_results_data.append([case_name_iter, "NA", "NA", "NA"])

        all_results_data.sort(key=lambda x: x[0])

        with open(config.report_file, "a", newline='') as rf_csv:
            writer = csv.writer(rf_csv)
            for row_data in all_results_data:
                writer.writerow(row_data)

        print(f"\n--- Script Finished. Report at {config.report_file} ---")

if __name__ == "__main__":
    main()
