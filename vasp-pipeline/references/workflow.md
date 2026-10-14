# Fluxo VASP — etapas

Conteúdo: [1 Convergência](#1-convergência) · [2 Relaxação/estático](#2-relaxação-e-estático) · [3 Propriedades](#3-propriedades-eletrônicas) · [4 Superfícies](#4-slabs-energia-de-superfície-wulff) · [5 Defeitos](#5-dopagem-vacâncias-energia-de-formação) · [6 Moléculas/DFPT](#6-moléculas-dfpt-phonopy-wannier)

Estrutura de pastas observada: `<material>/paw_pbe_2xENMAX_Stress[_OK]/`, `paw_pbe_1.125xENMAX_Etot/`, `..._DOS[_OK]/`, `..._bands/`, `pristine_materials_stress/` (constituintes), `DEFECT_MODELS/`, `doping_studies/`. Fases polimórficas em subpastas (`ZrO2_<fase>_…`).

## 1. Convergência
- **ENCUT:** 2×ENMAX para o passo de stress (ISIF=3); 1.125×ENMAX para energia total. ENMAX = o maior dentre os POTCAR usados (`grep ENMAX POTCAR`).
- **k-points:** por densidade (o tipo de malha usado em cada projeto não está documentado: conferir o `KPOINTS` existente); critério explícito (Δ meV/átomo e ΔV %). Pastas numeradas por malha/cutoff (`15/`, `20/`, …) com um INCAR comum.
- Extração: `extract_stress_data.py` (último arquivo de cada pasta numerada → tabela), `convergence_table`-style em pandas. Verifique que a pasta rodou completa (não pegue CONTCAR parcial).
- Estequiometria/consistência: `check_stoichiometry.py` antes de comparar energias.

## 2. Relaxação e estático
- ISIF=3 (célula+íons) → ISIF=2 (íons, base reconstruída) como acima; `EDIFFG=-0.01`; `NSW=800`; `IBRION=2`.
- `jobex`-like retomada: o `CONTCAR` vira o novo `POSCAR` (copiar antes de reenviar); `STOPCAR` limpo no início do job.
- Geometria vinda de outro código (CP2K/Turbomole) → partir do `CONTCAR` do VASP define o *setting* dos índices (ex.: P2₁/c: (1̄11) ≠ (111)).
- Parâmetros de rede/volume: `extract_lattice_param.py` (lê `vasprun.xml`), `volume_strain_generator.py` para E(V).

## 3. Propriedades eletrônicas
- **DOS:** estático em malha mais densa, `LORBIT=10/11`, `NEDOS` alto; `dos_analysis.py` (pymatgen `Vasprun`, smearing Gaussiano σ), por elemento/orbital; dados em `DOS_raw_data.csv`. PDOS projetada (`plot_pdos.py`).
- **Bandas:** `ICHARG=11` a partir do `CHGCAR` do estático; `gen_kpath.py` (pymatgen `HighSymmKpath`, KPOINTS em modo linha) — o caminho depende da célula *primitiva padrão*; se o POSCAR não é a primitiva padrão, converter antes ou o caminho fica errado. `plot_bands.py`, `plot_bands_dos.py`, `gen_bandgap_table.py`.
- **Massa efetiva/transporte:** `extract_effective_mass.py` (lê uma tabela de transporte com Seebeck e concentração de portadores; tipo n/p pelo sinal do Seebeck; conferir o formato do CSV de entrada).
- **Magnetismo:** `ISPIN=2` + `MAGMOM`; comparar ordenações (paralela × antiparalela) por energia; guardar momento por átomo (`magnetic_moment_comparison.*`).
- **Híbrido (HSE06/PBE0)** e **GW**: custo alto; no plano de ML do BaZrS3 estão **planejados** (não executados) para 1–2 estruturas de referência, para delta-learning do gap (PBE subestima o gap).

## 4. Slabs, energia de superfície, Wulff
- Gerar com pymatgen: `SlabGenerator(... reorient_lattice=False)` — o padrão gira a rede e quebra a correspondência com [uvw] do bulk. `Slab.is_polar()` só vale com estados de oxidação. `extract_surfaces.py` enumera índices distintos por simetria.
- Aceitar só slabs **simétricos, estequiométricos e apolares** (Tasker I/II; III reconstruída para II); descartar fios, assimétricos, duplicatas.
- Espessura típica 12–15 Å, vácuo 15 Å (CP2K/GPW permite 25 Å quase de graça; em ondas planas o vácuo custa FFT — testar). `ISIF=2`, `k_z=1`; `IDIPOL=3` + `LDIPOL` quando as faces são quimicamente diferentes.
- **γ = (E_slab − n·E_bulk/f.u.)/(2A)** (`gama_calculator.py`, eV/Å²→J/m² ×16.0217662); E_bulk com **mesmos** ENCUT/PREC/densidade de k. Wulff: `wulff_generator.py` (pymatgen `WulffShape`, CONTCAR do bulk relaxado).
- Ligações quebradas/√Z não é proxy robusto em bcc; usar γ de DFT publicado (Materials Project/Tran 2016) para escolher planos.
- Ligas SQS (P1): o cortador do ZrO2 rejeita tudo (exige simetria) — usar corte em sítios ideais + deslocamento relaxado (`alloy_slab_cut.py`); γ por cópias inteiras do SQS.

## 5. Dopagem, vacâncias, energia de formação
- Gerar: `gen_doped_material.py` (dopagem/vacância com restrição de distância), `generate_doping_permutations.py`, `gen_perovskite_doping.py`, `build_doping_dataset.py` (CSV com Composition).
- **E_f formal** com potenciais químicos μ de referência (`bulk_pure.csv`/constituintes); `calculate_formation_energy.py` (balanço de massa). Diferença de energia total entre supercélulas **não** é energia de formação (sem μ).
- Energia de ligação de complexos: E_b = E(complexo) − E(A) − E(B) + E(puro) (negativo = estabiliza).
- **Erros já vistos:** réplicas com `vasprun.xml` MD5-idêntico (cópia acidental); dois lotes de cálculo (`_struc` × `_OK`) divergindo ~0,7–0,8 eV para qualquer estrutura com Ca — reconciliar antes de publicar; sempre rastrear cada linha de tabela ao `vasprun.xml`.
- Correção de supercélula (imagem periódica): testar tamanho (ex. 3×2×3) na configuração mais simples.

## 6. Moléculas, DFPT, phonopy, Wannier
- Molécula em caixa: PBE relax → DFPT estático (VASP padrão: `IBRION=8`, `LEPSILON=.TRUE.`; conferir o `INCAR.dfpt` do projeto) para cargas de Born e IR; phonopy a partir do DFPT; dois pós-processamentos de IR concordando a 1e-5 cm⁻¹ no caso da alizarina; Wannier90 (v3.1.0 × v4.0.1 cross-check, 44 MLWFs).
- Caixa grande, dipolo (`IDIPOL`, `LDIPOL`), convergência de vácuo/ENCUT são **pendências comuns** — não assumir convergência de uma escolha única.
- Cuidado com o nome da pasta: `alizarina_vasp_pbe_d3` tinha `IVDW=0` (sem D3). Sempre conferir o INCAR.
- Comparação com Turbomole/CP2K: mesma geometria de partida e mesma ordem de átomos; níveis diferentes (PAW-PBE ondas planas × def2-TZVP all-electron) — documentar.
