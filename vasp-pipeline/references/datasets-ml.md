# Datasets para potencial de ML (rattle / DeepMD) — roteiro do BaZrS3

Objetivo: dataset de treino de MLIP (DeepMD) para ligas/defeitos; o ML precisa de forças, não só energias de mínimos.

1. **Mínimos:** relaxar (ISIF=2) todas as combinações dopante/vacância mapeadas (Ca1/Ca2/Ca4, CaSv, Sv1/Sv2, Bav, CaBa, pristino). Ensina a termodinâmica.
2. **Rattle de deslocamento:** deslocamentos gaussianos 0.01–0.12 Å (`generate_rattled_structures.py`; distância mínima limitada pelo RCORE do POTCAR: Ba 2.3, Zr 2.1, S 1.9, Ca 2.5 Bohr) → SCF estático. Ensina curvatura (fônons/MD).
3. **Rattle volumétrico:** ±1 %, ±2 % de volume; deslocamentos sobre cada célula (20 réplicas × 6 amplitudes). Convenção de pasta plana `rattle_vol±Xpct_<amp>_<rep>` dentro de `volumetric_rattle/` (compatível com o regex de `prepare_ml_data.py`; não aninhar).
4. **Controle de tamanho:** supercélula maior numa configuração simples (imagem periódica).
5. **Configurações cruzadas aleatórias** para testar generalização.
6. **Referência cara:** HSE06/GW em ≥ 2 estruturas (pura e dopada) → delta-learning do gap.

Treino: `deepmd_train/` (400k passos no exemplo). **Reportar RMSE real**: 1,3–3,2 meV/átomo no primeiro treino (1380 frames/27 sistemas); número de apresentação deve vir do `lcurve`/teste, nunca de memória. EoS, mistura e MD só entram se existirem outputs.
Pós: `eos_calculator.py`, `calc_mixing_enthalpy.py`, `phase_stability.py`, `run_phonopy_deepmd.py`, `run_deepmd_ase_md_t_{inst,ramp}.py`, `convert_vasp_to_lammps.py`, `extract_parity_data.py`, `plot_free_energy.py`, `plot_defect_concentration.py`, `plot_transition_levels.py`.

Estratégia de publicação (usuário): artigo de benchmark de mono-dopagens (tendências periódicas: sítio A Sr×Ca, sítio B Ti×Hf) em revistas FI 2–4,5; co-doping+ML em FI 7+.
