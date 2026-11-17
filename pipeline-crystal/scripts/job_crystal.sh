#!/bin/bash
# job_crystal.sh -- CRYSTAL23 on harpia (crystalOMP: 1 process x 48 OpenMP threads; properties serial).
# Usage:
#   sbatch [-p par48a] [-t 3-00:00:00] job_crystal.sh <rundir>          # SCF / OPTGEOM from <rundir>/INPUT
#   sbatch -t 02:00:00 job_crystal.sh <rundir> props                     # properties < <rundir>/PROPS (needs fort.9)
# Inputs copied to scratch if present: INPUT, fort.34 (EXTERNAL), fort.9 -> fort.20 (GUESSP / RESTART),
#   OPTINFO.DAT + HESSOPT.DAT (OPTGEOM RESTART). Outputs copied back: fort.9 fort.34 OPTINFO.DAT HESSOPT.DAT
#   SCFOUT.LOG opt[ac]* fort.25 DOSS.DAT BAND.DAT.
# harpia: RAM limited to 900 MB/CPU -> --mem = 900M x CPUs (43200M for 48).
# Success is decided by TEXT in crystal.out (never by exit code / sacct COMPLETED).
#SBATCH -J cry
#SBATCH -p par48a
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=48
#SBATCH --mem=43200M
#SBATCH -t 3-00:00:00
#SBATCH -o cry_%j.out
#SBATCH -e cry_%j.err
set -u
DIR=$(readlink -f "${1:?rundir}")
MODE=${2:-crystal}

# --- environment block (mandatory in every job, user rule 2026-11-07) ---
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1} OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close OMP_STACKSIZE=512M
export MKL_NUM_THREADS=1
ulimit -s unlimited
module purge; module load modmat/crystal/23.1.0.1
# crystalOMP was linked against the oneAPI 2026.2 runtime; without this it fails to load libiomp5/libifcore
export LD_LIBRARY_PATH="/opt/intel/oneapi/compiler/2026.2/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
BIN="$CRY23_ROOT/bin/Linux-ifort_i64_omp/v1.0.1"

# --- stall watchdog (mandatory, user rule 2026-11-12). crystal.out lives in $DIR -> watch $DIR.
#     Hybrid gradients can go >1 h without writing: 2 h idle limit.
#     run_watched backgrounds the command (setsid ... &): bash then feeds it /dev/null as stdin, so
#     "run_watched crystalOMP < INPUT" dies with "END OF DATA IN INPUT DECK" -> redirect INSIDE bash -c.
source ~/skills/global/job_watchdog.sh
export WATCHDOG_DIR="$DIR" WATCHDOG_IDLE_SEC=${WATCHDOG_IDLE_SEC:-7200} WATCHDOG_LOG="$DIR/watchdog.log"

WORK=$HOME/scratch/crystal23/${SLURM_JOB_ID:-local$$}; mkdir -p "$WORK"; chmod 700 "$WORK"
cd "$WORK"
echo "job=${SLURM_JOB_ID:-} node=$(hostname) threads=$OMP_NUM_THREADS mode=$MODE dir=$DIR $(date)"

if [ "$MODE" = props ]; then
  [ -f "$DIR/fort.9" ] && [ -f "$DIR/PROPS" ] || { echo "FAIL: props needs $DIR/fort.9 and $DIR/PROPS"; exit 1; }
  cp "$DIR/fort.9" fort.9; cp "$DIR/PROPS" PROPS
  run_watched bash -c '"$0" < PROPS' "$BIN/properties" > "$DIR/props.out" 2>&1; rc=$?
  for f in fort.25 DOSS.DAT BAND.DAT; do [ -f $f ] && cp $f "$DIR/"; done
  [ $rc -eq 124 ] && { echo "FAIL: STALLED"; exit 1; }
  grep -aq "EEEEEEEEEE TERMINATION" "$DIR/props.out" && ! grep -aq "ERROR \*\*\*\*" "$DIR/props.out" \
    || { echo "FAIL: properties error:"; grep -a "ERROR" "$DIR/props.out" | head -3; exit 1; }
  echo "OK props $(date)"; exit 0
fi

cp "$DIR/INPUT" INPUT
[ -f "$DIR/fort.34" ] && cp "$DIR/fort.34" fort.34
[ -f "$DIR/fort.9" ] && cp "$DIR/fort.9" fort.20
for f in OPTINFO.DAT HESSOPT.DAT; do [ -f "$DIR/$f" ] && cp "$DIR/$f" .; done
if grep -q "^RESTART" INPUT && [ ! -f OPTINFO.DAT ]; then echo "FAIL: RESTART without OPTINFO.DAT"; exit 1; fi
# CRYSTAL appends nothing: keep the previous output when restarting
[ -f "$DIR/crystal.out" ] && mv "$DIR/crystal.out" "$DIR/crystal.out.$(date +%Y%m%d%H%M%S)"

run_watched bash -c '"$0" < INPUT' "$BIN/crystalOMP" > "$DIR/crystal.out" 2>&1; rc=$?
for f in fort.9 fort.34 OPTINFO.DAT HESSOPT.DAT SCFOUT.LOG; do [ -f $f ] && cp $f "$DIR/"; done
ls opta* optc* >/dev/null 2>&1 && { mkdir -p "$DIR/opt_steps"; cp opta* optc* "$DIR/opt_steps/" 2>/dev/null; }
grep -a -E "SCF ENDED|OPT END|ENERGY BAND GAP|TELAPSE" "$DIR/crystal.out" | tail -4
[ $rc -eq 124 ] && { echo "FAIL: STALLED (watchdog)"; exit 1; }
grep -aq "EEEEEEEEEE TERMINATION" "$DIR/crystal.out" || { echo "FAIL: no 'EEEEEEEEEE TERMINATION'"; exit 1; }
grep -aq "SCF ENDED - CONVERGENCE" "$DIR/crystal.out" || { echo "FAIL: SCF not converged"; exit 1; }
if grep -q "^OPTGEOM" INPUT; then grep -aq "OPT END - CONVERGED" "$DIR/crystal.out" || { echo "FAIL: optimization not converged (restart: add RESTART, keep OPTINFO.DAT + fort.9)"; exit 1; }; fi
echo "OK $(date)"
