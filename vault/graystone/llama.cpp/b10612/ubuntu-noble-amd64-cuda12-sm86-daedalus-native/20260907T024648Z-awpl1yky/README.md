# llama.cpp b10612 - Daedalus native build

## Artifact identity
- Upstream: https://github.com/ggml-org/llama.cpp.git
- Source commit: 7584430716ee229751771ed0d6bbcb780d105eeb
- Configuration: ubuntu-noble-amd64-cuda12-sm86-daedalus-native
- Captured at UTC: 2026-09-07T02:46:48.335973+00:00
- Archive: llama-runtime.tar.gz
- SHA256: 2d4c97b86051b8522d4c51d35b495cf06f4f5bdb048200501aa72004af444fc4

The timestamp records capture, not original compilation.
This is a local build, not an upstream prebuilt release.

## Recorded hardware and software
- Machine: Daedalus
- CPU: Intel Core i9-11900K; exact flags in evidence/cpu.txt.
- OS: Ubuntu 24.04.4 LTS, Noble, amd64.
- GPU: NVIDIA GeForce RTX 3090, 24 GB.
- CUDA target: SM86 / compute capability 8.6.
- CPU optimization: GGML_NATIVE=ON (-march=native).
- C/C++ compilers: GCC/G++ 13.3.0.
- CUDA toolkit: 12.0.140, Ubuntu nvidia-cuda-toolkit.
- CUDA host compiler: GNU 12.4.0, reported by build log.
- CMake: 3.28.3; Release build; shared libraries enabled.

Captured GPU and driver: NVIDIA GeForce RTX 3090, 8.6, 595.84

Captured kernel: Linux daedalus-01 6.8.0-100-generic #100-Ubuntu SMP PREEMPT_DYNAMIC Tue Jan 13 16:40:06 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux

## Deployment requirements
Preserve runtime/bin, runtime/lib, and their symbolic links.
Library search path: $ORIGIN:$ORIGIN/../lib.
Ubuntu and CUDA system libraries must be installed separately.
See evidence/linked-libraries.txt for observed library resolution.
The full installed-package inventory is evidence, not a minimal
runtime dependency manifest.

Driver 595.84 is the recorded baseline, not a proven minimum.
Other driver versions have not been validated for this artifact.
Other CPUs require compatibility checks because this build uses
native CPU instructions. Other GPU targets may require rebuilding.

## Validation
Passed: compilation, installation, expected server version,
installed library resolution without LD_LIBRARY_PATH, and
SHA256 verification after transfer to Athena.

Pending: clean buildless deployment and Muse image processing
through Hermes using this specific artifact.

Models, projectors, Hermes, and service configuration are separate.
Detailed hardware and toolchain records are in evidence/.
