# INCAR, KPOINTS, job.sh e scripts

## INCAR de referência (BaZrS3, estático/relax)
```
SYSTEM = <material>
ENCUT  = <1.125*ENMAX | 2*ENMAX>
ALGO   = Normal ; NELMIN = 6 ; NELM = 1500 ; NELMDL = -8
EDIFF  = 1.0E-6 ; AMIX = 0.4 ; BMIX = 0.0001
GGA    = PE
PREC   = Accurate ; ISPIN = 1 ; ADDGRID = .TRUE. ; LASPH = .TRUE. ; LREAL = Auto
NSW    = 800 ; EDIFFG = -0.0100 ; IBRION = 2 ; ISIF = 3 (stress) | 2 (Etot) ; POTIM = 0.5
ISMEAR = 0 ; SIGMA = 0.01
LORBIT = 10 ; NWRITE = 1
LWAVE = .FALSE. ; LCHARG = .FALSE. ; LELF = .FALSE. ; LAECHG = .FALSE.   # LAECHG p/ Bader
NCORE  = 4 ; LPLANE = .TRUE.
# magnético: ISPIN=2 + MAGMOM = N*valor (VOSKOWN=1 aparece comentado no INCAR do grupo, p/ sistemas magnéticos)
# híbrido: LHFCALC=.TRUE. ; AEXX=0.25 ; HFSCREEN=0.206 ; PRECFOCK=Normal ; LMAXFOCK=4
# pressão externa: PSTRESS (kbar)
```
Se a convergência eletrônica falhar: reduzir `TIME`, ajustar `AMIX/BMIX`, `ALGO=All`/`Fast` com cuidado, `LMAXMIX=4/6` (d/f). Sloshing (`DAV: 99/100` repetido) aparece no `OSZICAR`.

## job.sh (access)
```bash
#!/bin/bash
#SBATCH -t 24:00:00
#SBATCH -N 2 --ntasks-per-node=8 -n 16 --cpus-per-task=1
#SBATCH -o job.out -e job.erro -J <nome>
ulimit -s unlimited ; ulimit -l unlimited
module purge
module load miniconda/24.4.0-libmamba intel/mpi/2017 vasp/6.4.3
export I_MPI_HYDRA_BOOTSTRAP=slurm OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=1
export OMP_PLACES=cores OMP_PROC_BIND=close I_MPI_PIN=1 I_MPI_PIN_DOMAIN=omp
export I_MPI_FABRICS=shm:ofi I_MPI_FALLBACK=0
# se o fabric do access estiver instável (ver SKILL.md §3):
# export OMPI_MCA_pml=ob1 OMPI_MCA_btl=self,sm,tcp OMPI_MCA_btl_ofi_disable=1
cd $SLURM_SUBMIT_DIR
rm -f STOPCAR
mpirun -np $SLURM_NTASKS vasp_std > saida.out
```
Arrays de pastas: `--array=1-N%M` e `sed -n "${SLURM_ARRAY_TASK_ID}p"` numa lista em FS compartilhado.

## Radar de fila (`check_queue.py`)
Percorre subpastas com `INCAR`; usa `OUTCAR` (sucesso: `reached required accuracy`) e `OSZICAR` (erro: `DAV: 100`/`DAV:  99`). Útil depois de arrays grandes (rattle: milhares de pastas).

## Scripts (em `~/work_vasp/scripts/`)
| Categoria | Scripts |
|---|---|
| Estrutura | `super_cell_gen.py`, `ordenating_POSCAR.py`, `volume_strain_generator.py`, `generate_rattled_structures.py`, `gen_doped_material.py`, `generate_doping_permutations.py`, `gen_perovskite_doping.py`, `extract_surfaces.py`, `alloy_slab_cut.py` |
| Extração | `extract_stress_data.py`, `extract_lattice_param.py`, `extract_thermo.py`, `extract_xdatcar.py`, `check_stoichiometry.py`, `build_doping_dataset.py`, `calculate_formation_energy.py` |
| Propriedades | `dos_analysis.py`, `gen_kpath.py`, `gen_bandgap_table.py`, `extract_effective_mass.py`, `gama_calculator.py`, `wulff_generator.py` |
| Figuras | `plot_dos.py`, `plot_bands.py`, `plot_bands_dos.py`, `plot_chg.py`, `plot_stress.py`, `plot_thermo.py`, `visualizar_poscar.py` |
| ML / fonons | `scripts/ML/*` (prepare_ml_data, eos_calculator, extract_parity_data, run_deepmd_ase_md_*, phase_stability, …), `scripts/phonopy/` |
| Materials Project | `materials_project_properties_download.py` — **nunca com chave API no código** (já houve chave hardcoded removida antes do push) |
