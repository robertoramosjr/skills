#!/bin/bash
# job_crystal.sh -- CRYSTAL23 on harpia. Runs one or MANY run dirs sequentially in one allocation
# (VASP-rito style, like bash_stress_coaraci.sh): converged dirs are skipped, an interrupted OPTGEOM is
# restarted (RESTART + OPTINFO.DAT + fort.9->fort.20), and the job resubmits itself when the walltime
# left is below RESUBMIT_MARGIN_MIN (default 90 min, as the VASP script).
#
# Usage:
#   sbatch job_crystal.sh DIR [DIR ...]             # DIR has INPUT, or is a parent whose subdirs have INPUT
#   sbatch job_crystal.sh runs/hse_stress_kconv     # k-convergence: 05 10 ... 50 in sequence
#   sbatch -t 04:00:00 job_crystal.sh --props DIR   # properties < DIR/PROPS (needs DIR/fort.9)
#   sbatch --export=ALL,LAYOUT=hybrid job_crystal.sh DIR   # layout override: omp | hybrid | mpi
# Success is decided by TEXT in crystal.out (never by exit code / sacct COMPLETED).
#
# --- Allocation (harpia, verified 2026-11-17; SKILL.md §2) -------------------------------------------
# harpia = 1 node, 2 sockets x 32 cores x 2 hyperthreads = 128 Slurm CPUs (SelectTypeParameters=CR_CPU_MEMORY).
# Slurm hands out WHOLE CORES as hyperthread pairs: 48 CPUs = 24 physical cores + their siblings
# (job 879 cpuset 0-23,64-87). QoS harpia_48a/b: max 48 CPUs and 48 GB per user; RAM 900 MB/CPU.
# Same header for every layout: 24 tasks x 2 CPUs (one task per physical core).
#SBATCH -J cry
#SBATCH -p par48a
#SBATCH -N 1
#SBATCH --ntasks=24
#SBATCH --cpus-per-task=2
#SBATCH --mem=43200M
#SBATCH -t 3-00:00:00
#SBATCH -o cry_%j.out
#SBATCH -e cry_%j.err
set -u
SELF=$(readlink -f "$0")
[ -n "${SLURM_JOB_ID:-}" ] && SELF=$(scontrol show job "$SLURM_JOB_ID" | sed -n 's/^ *Command=\([^ ]*\).*/\1/p')
PROPS=0; [ "${1:-}" = "--props" ] && { PROPS=1; shift; }
[ $# -ge 1 ] || { echo "usage: job_crystal.sh [--props] DIR [DIR ...]"; exit 1; }
ARGS=("$@")
RESUBMIT_MARGIN_MIN=${RESUBMIT_MARGIN_MIN:-90}
LAYOUT=${LAYOUT:-omp}

# ================= environment block (mandatory in every CRYSTAL job; harpia, benchmark 879/893) =================
NCPU=${SLURM_CPUS_ON_NODE:-$(nproc)}            # 48 = 24 cores x 2 hyperthreads
NTASK=${SLURM_NTASKS:-$(( NCPU / 2 ))}          # 24 = one per physical core
module purge; module load modmat/crystal/23.1.0.1
OMPI=/home/hpc/software/openmpi/4.1.8-orca       # Pcrystal/PcrystalOMP need libmpi.so.40 (OpenMPI 4.1.x); not in the module
export PATH=$OMPI/bin:$PATH
export LD_LIBRARY_PATH=$OMPI/lib:/opt/intel/oneapi/compiler/2026.2/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}  # Intel runtime of the binaries
export OMP_DYNAMIC=FALSE OMP_STACKSIZE=512M MKL_NUM_THREADS=1 MKL_DYNAMIC=FALSE
export OMP_PROC_BIND=close OMP_PLACES=threads   # one OpenMP thread per hardware thread, packed core by core
ulimit -s unlimited
BIN_OMP=$CRY23_ROOT/bin/Linux-ifort_i64_omp/v1.0.1
BIN_MPI=$CRY23_ROOT/bin/Linux-ifort_i64/v1.0.1
launcher() {   # $1 = crystal | props  -> sets CMD and OMP_NUM_THREADS (call WITHOUT $(...): a subshell loses the export)
  case "$LAYOUT:$1" in
    omp:crystal)    export OMP_NUM_THREADS=$NCPU; CMD="$BIN_OMP/crystalOMP" ;;          # 1 process x 48 threads (FASTEST, 879)
    omp:props)      export OMP_NUM_THREADS=$NCPU; CMD="$BIN_OMP/properties" ;;
    hybrid:crystal) export OMP_NUM_THREADS=$(( NCPU / NTASK ))
                    CMD="mpirun -np $NTASK --map-by core --bind-to core -x OMP_NUM_THREADS -x OMP_PLACES -x OMP_PROC_BIND -x OMP_STACKSIZE -x LD_LIBRARY_PATH $BIN_OMP/PcrystalOMP" ;;
    mpi:crystal)    export OMP_NUM_THREADS=1
                    CMD="mpirun -np $NTASK --map-by core --bind-to core -x LD_LIBRARY_PATH $BIN_MPI/Pcrystal" ;;
    hybrid:props|mpi:props) export OMP_NUM_THREADS=1
                    CMD="mpirun -np $NTASK --map-by core --bind-to core -x LD_LIBRARY_PATH $BIN_MPI/Pproperties" ;;
    *) echo "FAIL: unknown LAYOUT=$LAYOUT (omp|hybrid|mpi)"; exit 1 ;;
  esac
}
# =================================================================================================================

source ~/skills/global/job_watchdog.sh              # mandatory (user rule 2026-11-12); stdin preserved since 2026-11-17
export WATCHDOG_IDLE_SEC=${WATCHDOG_IDLE_SEC:-7200}  # hybrid gradients can go >1 h without writing

remaining_min() {  # walltime left (min), from squeue %L
  local s; s=$(squeue -h -j "${SLURM_JOB_ID:-0}" -o %L 2>/dev/null)
  [ -z "$s" ] || [ "$s" = "UNLIMITED" ] && { echo 99999; return; }
  local d=0 h=0 m=0 a b c; [[ $s == *-* ]] && { d=${s%%-*}; s=${s#*-}; }
  IFS=: read -r a b c <<< "$s"
  if [ -n "${c:-}" ]; then h=$a; m=$b; elif [ -n "${b:-}" ]; then m=$a; fi
  echo $(( 10#$d*1440 + 10#$h*60 + 10#$m ))
}
is_done() {  # $1 = dir
  local o="$1/crystal.out"
  [ -f "$o" ] && grep -aq "EEEEEEEEEE TERMINATION" "$o" && grep -aq "SCF ENDED - CONVERGENCE" "$o" || return 1
  if grep -q "^OPTGEOM" "$1/INPUT"; then   # old inputs without ONELOG print the opt end in SCFOUT.LOG
    grep -aq "OPT END - CONVERGED" "$o" "$1/SCFOUT.LOG" 2>/dev/null || return 1; fi
  return 0
}
resubmit() {
  echo "[resubmit] $(remaining_min) min left (margin ${RESUBMIT_MARGIN_MIN}): sbatch again"
  cd "$SUBMIT_DIR"; sbatch --export=ALL,LAYOUT=$LAYOUT "$SELF" $([ $PROPS = 1 ] && echo --props) "${ARGS[@]}"; exit 0
}

SUBMIT_DIR=${SLURM_SUBMIT_DIR:-$PWD}
DIRS=()
for d in "${ARGS[@]}"; do
  d=$(readlink -f "$d")
  if [ -f "$d/INPUT" ] || [ $PROPS = 1 ]; then DIRS+=("$d")
  else for s in $(ls -d "$d"/*/ 2>/dev/null | sort); do [ -f "$s/INPUT" ] && DIRS+=("${s%/}"); done; fi
done
echo "job=${SLURM_JOB_ID:-local} node=$(hostname) layout=$LAYOUT ncpu=$NCPU ntask=$NTASK cpuset=$(grep Cpus_allowed_list /proc/self/status | cut -f2) dirs=${#DIRS[@]} $(date)"

for DIR in "${DIRS[@]}"; do
  WORK=$HOME/scratch/crystal23/${SLURM_JOB_ID:-local$$}/$(basename "$DIR"); mkdir -p "$WORK"; chmod 700 "$WORK"
  cd "$WORK"; rm -f "$DIR/STALLED"
  export WATCHDOG_DIR="$DIR" WATCHDOG_LOG="$DIR/watchdog.log"
  if [ $PROPS = 1 ]; then
    [ -f "$DIR/fort.9" ] && [ -f "$DIR/PROPS" ] || { echo "FAIL $DIR: needs fort.9 and PROPS"; continue; }
    cp "$DIR/fort.9" fort.9; cp "$DIR/PROPS" PROPS; cp PROPS INPUT
    launcher props
    run_watched $CMD < PROPS > "$DIR/props.out" 2>&1
    for f in fort.25 DOSS.DAT BAND.DAT; do [ -f $f ] && cp $f "$DIR/"; done
    if grep -aq "EEEEEEEEEE TERMINATION" "$DIR/props.out" && ! grep -aq "ERROR \*\*\*\*" "$DIR/props.out"; then echo "OK props $DIR"
    else echo "FAIL props $DIR: $(grep -a ERROR "$DIR/props.out" | head -2)"; fi
    continue
  fi
  if is_done "$DIR"; then echo "skip $DIR (converged)"; continue; fi
  (( $(remaining_min) < RESUBMIT_MARGIN_MIN )) && resubmit
  cp "$DIR/INPUT" INPUT                             # Pcrystal reads the file INPUT; crystalOMP reads stdin
  [ -f "$DIR/fort.34" ] && cp "$DIR/fort.34" fort.34
  [ -f "$DIR/fort.9" ] && cp "$DIR/fort.9" fort.20
  for f in OPTINFO.DAT HESSOPT.DAT; do [ -f "$DIR/$f" ] && cp "$DIR/$f" .; done
  if grep -q "^OPTGEOM" INPUT && [ -f OPTINFO.DAT ] && ! grep -q "^RESTART" INPUT; then
    sed -i '/^OPTGEOM/a RESTART' INPUT; echo "restart OPTGEOM in $DIR (OPTINFO.DAT found)"
  fi
  [ -f "$DIR/crystal.out" ] && mv "$DIR/crystal.out" "$DIR/crystal.out.$(date +%Y%m%d%H%M%S)"
  # stop ~20 min before the walltime so files are copied back and the job can resubmit itself
  LIMIT=$(( ($(remaining_min) - 20) * 60 )); (( LIMIT > 2592000 )) && LIMIT=2592000
  launcher crystal
  run_watched timeout --signal=TERM "$LIMIT" $CMD < INPUT > "$DIR/crystal.out" 2>&1; rc=$?
  for f in fort.9 fort.34 OPTINFO.DAT HESSOPT.DAT SCFOUT.LOG; do [ -f $f ] && cp $f "$DIR/"; done
  ls opta* optc* >/dev/null 2>&1 && { mkdir -p "$DIR/opt_steps"; cp opta* optc* "$DIR/opt_steps/" 2>/dev/null; }
  grep -a -E "SCF ENDED|OPT END|ENERGY BAND GAP|TELAPSE" "$DIR/crystal.out" | tail -3
  if [ -f "$DIR/STALLED" ]; then echo "FAIL $DIR: STALLED (watchdog)"; continue; fi
  if is_done "$DIR"; then echo "OK $DIR $(date)"; continue; fi
  [ $rc -eq 124 ] && resubmit                        # walltime guard hit: continue in a new job (RESTART)
  echo "FAIL $DIR (rc=$rc): $(grep -a -m2 'ERROR' "$DIR/crystal.out")"
done
rm -rf "$HOME/scratch/crystal23/${SLURM_JOB_ID:-local$$}"
echo "END $(date)"
