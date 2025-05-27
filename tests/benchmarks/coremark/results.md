## TLDR

 - With Prof Info: 20943.504896
 - Native: 27037.988374
 - AOT noOPT: 23263.929278 = 0.86 * native
 - AOT PGO OPT: 23626.698169 = 0.874 * native = +1.56% over non-opt

## Output

```
2K performance run parameters for coremark.
CoreMark Size    : 666
Total ticks      : 19099
Total time (secs): 19.099000
Iterations/Sec   : 20943.504896
Iterations       : 400000
Compiler version : Clang 19.1.5-wasi-sdk (https://github.com/llvm/llvm-project ab4b5a2db582958af1ee308a790cfdb42bd24720)
Compiler flags   : -O3 -DPERFORMANCE_RUN=1
Memory location  : Please put data memory location here
                        (e.g. code in flash, data on heap etc)
seedcrc          : 0xe9f5
[0]crclist       : 0xe714
[0]crcmatrix     : 0x1fd7
[0]crcstate      : 0x8e3a
[0]crcfinal      : 0x65c5
Correct operation validated. See README.md for run and reporting rules.
CoreMark 1.0 : 20943.504896 / Clang 19.1.5-wasi-sdk (https://github.com/llvm/llvm-project ab4b5a2db582958af1ee308a790cfdb42bd24720) -O3 -DPERFORMANCE_RUN=1 / Heap
LLVM raw profile file coremark.profraw was generated.

Merge the raw profile data to coremark.profdata ..

Compile coremark.wasm to coremark_opt.aot with the profile data ..
Create AoT compiler with:
  target:        x86_64
  target cpu:    skylake-avx512
  target triple: x86_64-unknown-linux-gnu
  cpu features:
  opt level:     3
  size level:    3
  output format: AoT file
Compile success, file coremark_opt.aot was generated.

Run the coremark native
2K performance run parameters for coremark.
CoreMark Size    : 666
Total ticks      : 14794
Total time (secs): 14.794000
Iterations/Sec   : 27037.988374
Iterations       : 400000
Compiler version : Clang 20.1.4 (https://github.com/llvm/llvm-project ec28b8f9cc7f2ac187d8a617a6d08d5e56f9120e)
Compiler flags   : -O3 -DPERFORMANCE_RUN=1  -lrt
Memory location  : Please put data memory location here
                        (e.g. code in flash, data on heap etc)
seedcrc          : 0xe9f5
[0]crclist       : 0xe714
[0]crcmatrix     : 0x1fd7
[0]crcstate      : 0x8e3a
[0]crcfinal      : 0x65c5
Correct operation validated. See README.md for run and reporting rules.
CoreMark 1.0 : 27037.988374 / Clang 20.1.4 (https://github.com/llvm/llvm-project ec28b8f9cc7f2ac187d8a617a6d08d5e56f9120e) -O3 -DPERFORMANCE_RUN=1  -lrt / Heap

Run the original aot file coremark.aot
2K performance run parameters for coremark.
CoreMark Size    : 666
Total ticks      : 17194
Total time (secs): 17.194000
Iterations/Sec   : 23263.929278
Iterations       : 400000
Compiler version : Clang 19.1.5-wasi-sdk (https://github.com/llvm/llvm-project ab4b5a2db582958af1ee308a790cfdb42bd24720)
Compiler flags   : -O3 -DPERFORMANCE_RUN=1
Memory location  : Please put data memory location here
                        (e.g. code in flash, data on heap etc)
seedcrc          : 0xe9f5
[0]crclist       : 0xe714
[0]crcmatrix     : 0x1fd7
[0]crcstate      : 0x8e3a
[0]crcfinal      : 0x65c5
Correct operation validated. See README.md for run and reporting rules.
CoreMark 1.0 : 23263.929278 / Clang 19.1.5-wasi-sdk (https://github.com/llvm/llvm-project ab4b5a2db582958af1ee308a790cfdb42bd24720) -O3 -DPERFORMANCE_RUN=1 / Heap

Run the PGO optimized aot file coremark_opt.aot
2K performance run parameters for coremark.
CoreMark Size    : 666
Total ticks      : 16930
Total time (secs): 16.930000
Iterations/Sec   : 23626.698169
Iterations       : 400000
Compiler version : Clang 19.1.5-wasi-sdk (https://github.com/llvm/llvm-project ab4b5a2db582958af1ee308a790cfdb42bd24720)
Compiler flags   : -O3 -DPERFORMANCE_RUN=1
Memory location  : Please put data memory location here
                        (e.g. code in flash, data on heap etc)
seedcrc          : 0xe9f5
[0]crclist       : 0xe714
[0]crcmatrix     : 0x1fd7
[0]crcstate      : 0x8e3a
[0]crcfinal      : 0x65c5
Correct operation validated. See README.md for run and reporting rules.
CoreMark 1.0 : 23626.698169 / Clang 19.1.5-wasi-sdk (https://github.com/llvm/llvm-project ab4b5a2db582958af1ee308a790cfdb42bd24720) -O3 -DPERFORMANCE_RUN=1 / Heap
```
