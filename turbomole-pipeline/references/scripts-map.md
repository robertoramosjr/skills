# Mapa de scripts

Repo: `~/work_turbomole/scripts/` (`git@github.com:robertoramosjr/turbomole.git`, `main`). **Layout misto desde 2026-09-24:** parte dos scripts está na raiz do repo e parte em `scripts/scripts/` (movidos pelo remoto). Antes de chamar um script, `ls scripts/<nome> scripts/scripts/<nome>` — não assuma o caminho antigo. Use `git status/log` em vez de mtime. Nada pesado no login node; todos os `job_*.sh` vão por `sbatch`.

Confirmado nesta data: na raiz estão `xyz_to_coord.py`, `setup_hse06_opt_template.py`, `setup_cosmo_job.py`, `setup_population_job.py`, `run_freeh_thermal_correction.py`, `job_reference_compound_pipeline.sh`, `compute_pka_thermodynamic_cycle.py`, `calibrate_pka_pair.py`, `summarize_pka_calibration.py`, etc.; em `scripts/scripts/`: `parse_*.py`, `setup_*_template.py` (hse06_tzvp, r2scan3c, pbe0_svp, gw_bse, metal_complex), `job_crest_search.sh`, `job_r2scan3c_optimize.sh`, `job_pbe0_ir_uvvis.sh`, `job_hse06_labeling*.sh`, `job_metal_complex_pipeline.sh`, `filter_boltzmann_population.py`, `fanout_*_jobs.py`, `build_protonation_state.py`, `build_population_weighted_spectrum.py`, `render_cube_isosurface.py`, `select_active_learning_subset.py`.

## Por estágio

| Estágio | Scripts |
|---|---|
| 0 geometria | `xyz_to_coord.py`, `poscar_to_xyz.py`, `build_protonation_state.py` |
| Templates `define` | `setup_hse06_tzvp_template.py` (escf), `setup_hse06_opt_template.py` (opt tight), `setup_r2scan3c_template.py`, `setup_pbe0_svp_template.py`, `setup_gw_bse_template.py`, `setup_metal_complex_template.py`, `prepare_functional_benchmark.py` |
| Funil | `job_crest_search.sh`, `job_crest_search_alpb.sh`, `filter_boltzmann_population.py`, `job_r2scan3c_optimize.sh`, `rerank_layer_a_dft.py`, `select_active_learning_subset.py`, `fanout_conformer_jobs.py`, `fanout_labeled_subset_jobs.py`, `job_hse06_labeling*.sh` |
| Água | `job_water_tier2_*.sh`, `job_water_reopt.sh` (retoma capados), `reopt_convergence_report.py` (quão perto do critério ficou cada otimização), `job_solvent_relax*.sh`, `setup_water_extension.py`, `analyze_vacuum_vs_water_pka.py`, `xtb_solvation_on_dft_geometries.py`, `job_xtb_alpb_rerank.sh`, `analyze_alpb_rerank.py` |
| Propriedades | `job_pbe0_ir_uvvis.sh`, `job_population_analysis.sh`, `job_dscf_pop.sh`, `job_resume_force_pop.sh`, `job_pbe0_continue.sh`, `job_tm_native_sh_s0.sh` |
| Extração | `parse_bader.py`, `parse_excitations.py`, `parse_ir.py`, `parse_mulliken.py`, `parse_bond_order.py`, `parse_dos.py`, `parse_becke_pdos.py`, `parse_dos_scpa.py`, `parse_scpa_pdos_angular.py`, `parse_qpenergies_dos.py`, `parse_homo_lumo.py`, `compute_rdf.py`, `compare_charges.py`, `group_average_charges.py`, `compute_exciton_binding.py`, `compare_functionals.py`, `compare_low_states.py`, `convergence_table.py` |
| ML / auditoria | `apply_b1_model.py`, `apply_b2_osc_surrogate.py`, `audit_b1_features.py`, `permutation_test_b1_features.py`, `feature_selection_protocol.md`, `estimate_model_gap_impact.py`, `build_b2_consolidated_dataset.py`, `analyze_stda_state_selection.py` |
| Termodinâmica | `run_freeh_thermal_correction.py`, `setup_cosmo_job.py`, `extract_cosmo_energy.py`, `compute_pka_thermodynamic_cycle.py`, `assemble_state_pka_thermo.py`, `calibrate_pka_pair.py`, `summarize_pka_calibration.py`, `job_reference_compound_pipeline.sh` |
| Espectros/figuras | `build_population_weighted_spectrum.py`, `predict_uvvis_vs_ph.py`, `plot_speciation_vs_ph.py`, `veusz/plot_*.py`, `plot_b2_final_spectrum_matplotlib.py`, `render_cube_isosurface.py`, `prepare_paper2_3d_assets.py` |

## Convenções

- Docstring com `Usage:` no topo (vale como `--help`); `argparse`; nada hardcoded da molécula.
- **Específicos de artepilina C** (não reaproveitar sem revisar): `veusz/plot_bond_order_artepillinC.py`, `plot_bond_order_structure_artepillinC.py`, `plot_molecule_vesta_style.py`.
- `veusz/plot_dos.py` e `veusz/plot_rdf.py` têm flags locais (`--element4-label`, `--homo-lumo`, `--columns`) que um merge do upstream já derrubou — conferir flags antes de aceitar versão remota.
- Dependências: parsers só `numpy`; Veusz embedding via `veusz_env`; rdkit/ase/povray só em `vasp_env`.
- Documentos companheiros no repo: `MANUAL.md` (fluxo completo), `README.md` (referência dos scripts), `pipeline_extracao_dft.md` (checklist), `protonation_and_conformer_investigation.md` (registro narrativo do Paper 2), `feature_selection_protocol.md`.
- `scripts/tm_spectra.py` (IR `vibspectrum` + UV-vis `exspectrum` → `.dat` ampliados; `--ir-scale`, `--uv-fwhm`) · `scripts/tm_dos.py` (tm2molden + Multiwfn → `dos_tdos.dat`, gap). Ambos agem na pasta atual, argparse. Jobs coaraci: `job_raman_egrad_gpu.sh`, `job_gpu_aoforce_test.sh` em `work_turbomole/metal_complexes/scripts/scripts/`.
