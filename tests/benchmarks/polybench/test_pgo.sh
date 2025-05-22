#!/bin/bash

# Copyright (C) 2019 Intel Corporation.  All rights reserved.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

CUR_DIR=$PWD
OUT_DIR=$CUR_DIR/out
REPORT=$CUR_DIR/report.txt
TIME=/usr/bin/time

PLATFORM=$(uname -s | tr A-Z a-z)
if [ "$1" = "--sgx" ] && [ "$PLATFORM" = "linux" ]; then
    IWASM_CMD="$CUR_DIR/../../../product-mini/platforms/${PLATFORM}-sgx/enclave-sample/iwasm"
    WAMRC_CMD="$CUR_DIR/../../../wamr-compiler/build/wamrc -sgx"
else
    IWASM_CMD="$CUR_DIR/../../../product-mini/platforms/${PLATFORM}/build/iwasm"
    WAMRC_CMD="$CUR_DIR/../../../wamr-compiler/build/wamrc"
fi

BENCH_NAME_MAX_LEN=20

POLYBENCH_CASES="2mm 3mm adi atax bicg cholesky correlation covariance \
                 deriche doitgen durbin fdtd-2d floyd-warshall gemm gemver \
                 gesummv gramschmidt heat-3d jacobi-1d jacobi-2d ludcmp lu \
                 mvt nussinov seidel-2d symm syr2k syrk trisolv trmm"

rm -f $REPORT
touch $REPORT

function print_bench_name()
{
    name=$1
    echo -en "$name" >> $REPORT
    name_len=${#name}
    if [ $name_len -lt $BENCH_NAME_MAX_LEN ]
    then
        spaces=$(( $BENCH_NAME_MAX_LEN - $name_len ))
        for i in $(eval echo "{1..$spaces}"); do echo -n " " >> $REPORT; done
    fi
}

pushd $OUT_DIR > /dev/null 2>&1
for t in $POLYBENCH_CASES
do
    if [ ! -e "${t}.wasm" ]; then
        echo "${t}.wasm doesn't exist, please run build.sh first"
        exit
    fi

    # Compile .wasm to .aot
    if [ ! -e "${t}.aot" ]; then
        echo ""
        echo "Compile ${t}.wasm to ${t}.aot .."
        ${WAMRC_CMD} -o ${t}.aot ${t}.wasm
    else
        echo ""
        echo "${t}.aot already exists, skipping."
    fi

    # Compile .wasm to _pgo.aot
    if [ ! -e "${t}_pgo.aot" ]; then
        echo ""
        echo "Compile ${t}.wasm to ${t}_pgo.aot .."
        ${WAMRC_CMD} --enable-llvm-pgo -o ${t}_pgo.aot ${t}.wasm
    else
        echo ""
        echo "${t}_pgo.aot already exists, skipping."
    fi

    # Generate profile data (.profdata)
    if [ ! -e "${t}.profdata" ]; then
        echo ""
        # Prerequisite: ${t}_pgo.aot must exist to generate .profraw
        if [ -e "${t}_pgo.aot" ]; then
            echo "Run ${t}_pgo.aot to generate the raw profile data (${t}.profraw) .."
            ${IWASM_CMD} --gen-prof-file=${t}.profraw --dir=. ${t}_pgo.aot

            # Prerequisite: ${t}.profraw must exist to merge
            if [ -e "${t}.profraw" ]; then
                echo "Merge the raw profile data to ${t}.profdata .."
                # Ensure .profdata is freshly created by the merge command
                if rm -f ${t}.profdata && /home/doellerer/ma/wasm-micro-runtime/tests/benchmarks/polybench/../../../core/deps/llvm/build/bin/llvm-profdata merge -output=${t}.profdata ${t}.profraw; then
                    if [ ! -e "${t}.profdata" ]; then # Double check creation
                        echo "Warning: Merge command for ${t}.profdata seemed to succeed but file is missing."
                    fi
                else
                    echo "Error: Failed to create ${t}.profdata from ${t}.profraw."
                fi
            else
                echo "Error: ${t}.profraw not generated. Cannot create ${t}.profdata for ${t}."
            fi
        else
            echo "Error: ${t}_pgo.aot not found. Cannot generate profile data for ${t}."
        fi
    else
        echo ""
        echo "${t}.profdata already exists, skipping profile generation."
    fi

    # Compile .wasm to _opt.aot with profile data
    if [ ! -e "${t}_opt.aot" ]; then
        echo ""
        # Prerequisite: ${t}.profdata must exist
        if [ -e "${t}.profdata" ]; then
            echo "Compile ${t}.wasm to ${t}_opt.aot with the profile data .."
            ${WAMRC_CMD} --use-prof-file=${t}.profdata -o ${t}_opt.aot ${t}.wasm
        else
            echo "Error: ${t}.profdata not found. Cannot compile ${t}_opt.aot for ${t}."
        fi
    else
        echo ""
        echo "${t}_opt.aot already exists, skipping."
    fi
done
popd > /dev/null 2>&1

echo "Start to run cases, the result is written to report.txt"

#run benchmarks
cd $OUT_DIR
echo -en "\t\t\t\t\t  native\tiwasm-aot\tiwasm-aot-pgo\n" >> $REPORT

# Create a temporary directory for partial reports
PARTIAL_REPORTS_DIR=$(mktemp -d)

MAX_JOBS=10
job_count=0

for t in $POLYBENCH_CASES
do
    # Limit the number of parallel jobs
    if [ "$job_count" -ge "$MAX_JOBS" ]; then
        wait -n # Wait for any job to finish
        job_count=$((job_count - 1))
    fi

    ( # Start a subshell for backgrounding
        REPORT_PART_TMP="${PARTIAL_REPORTS_DIR}/${t}.part"

        # Call print_bench_name and redirect its output to the partial report file
        # This function is defined earlier in the script and uses BENCH_NAME_MAX_LEN
        print_bench_name $t > "$REPORT_PART_TMP"

        CMD_NATIVE="./${t}_native"
        CMD_AOT="${IWASM_CMD} ${t}.aot"
        CMD_AOT_OPT="${IWASM_CMD} ${t}_opt.aot"

        HYPERFINE_CSV_TMP=$(mktemp)

        echo "Benchmarking $t with hyperfine (native, WAMR AOT, WAMR AOT+PGO) .."
        hyperfine --ignore-failure --warmup 1 --runs 2 \
            --export-csv "${HYPERFINE_CSV_TMP}" \
            "${CMD_NATIVE}" \
            "${CMD_AOT}" \
            "${CMD_AOT_OPT}" > /dev/null 2>&1 # Suppress hyperfine console output

        # Append hyperfine results to the partial report file
        awk -F',' 'NR > 1 {printf "\t%s", $2} END {printf "\n"}' "${HYPERFINE_CSV_TMP}" >> "$REPORT_PART_TMP"

        rm -f "${HYPERFINE_CSV_TMP}"
    ) & # Background the subshell
    job_count=$((job_count + 1)) # Increment job counter
done

# Wait for all background benchmark jobs to complete
wait

# Concatenate all partial report files into the main report file in the correct order
echo "Aggregating results into $REPORT ..."
for t in $POLYBENCH_CASES
do
    PART_FILE="${PARTIAL_REPORTS_DIR}/${t}.part"
    if [ -f "$PART_FILE" ]; then
        cat "$PART_FILE" >> $REPORT
    else
        # Handle cases where a partial report might be missing (e.g., if a sub-process failed catastrophically)
        # Create a placeholder line in the report for this missing benchmark part
        # This ensures the report structure is maintained.
        # BENCH_NAME_MAX_LEN is used here, assuming it's set as a global variable.
        error_line=$(printf "%-${BENCH_NAME_MAX_LEN}s" "$t")
        # Append \tNA for each expected metric column (native, aot, aot-pgo)
        error_line+="\tNA\tNA\tNA"
        echo -e "$error_line" >> $REPORT
        echo "Warning: Partial report for $t not found. Added placeholder to $REPORT."
    fi
done

# Clean up the temporary directory for partial reports
rm -rf "${PARTIAL_REPORTS_DIR}"
