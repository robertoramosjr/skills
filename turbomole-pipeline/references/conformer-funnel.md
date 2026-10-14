# Funil de confôrmeros × microestados (moléculas flexíveis)

Use quando a molécula tem rotores (prenilas, cadeias, OH/metilas livres) ou vários estados de protonação, e o observável medido é uma **média sobre o ensemble**. Caso trabalhado: artepilina C, Paper 2 (`artepillin-c-paper2-funil` no cofre). Ambiente conda `paper2_funnel`; `xtb` 6.6.1 (módulo `xtb/6.6.1`); `crest` e `scikit-learn` — conferir com `which crest` / `python -c "import sklearn"` antes de planejar (já faltaram).

## Arquitetura (duas camadas)

**Camada A — ensemble ponderado, sem ML.**
CREST (iMTD-GC)/GFN2-xTB por microestado → corte por população de Boltzmann acumulada (~95 %, 298 K) → refino DFT barato → espectro **médio ponderado** por estado (o espectro, não a lista top-N, é o entregável).

**Camada B — substitutos delta-learning, sobre o ensemble já filtrado** (não sobre o CREST bruto: o corte de população já implementa "não gaste DFT caro em conforme irrelevante").
- B1 = ν(C=O) (alvo: `aoforce` HSE06; baseline barato GFN2-xTB `xtb --hess`).
- B2 = S1 (E, f) (alvo: escf HSE06, 60 estados; baseline sTDA/`std2` sobre wavefunction r2SCAN-3c via `tm2molden`).
- Cada um com seu próprio ciclo de aprendizado ativo e sua própria curva de convergência; **mostrar a curva antes de combinar critério de parada**.

Não decida mudança de arquitetura sozinho — reporte e pergunte.

## Passos e parâmetros que valeram

1. **CREST:** `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` e `-T $SLURM_NTASKS` (senão dupla paralelização: logs de 500 MB–1 GB de "OpenBLAS Warning" e lentidão). Script: `job_crest_search.sh` (vácuo) / `job_crest_search_alpb.sh` (água, janela 8 kcal/mol — mais larga que os 6 do vácuo porque o ranking GFN2 é ruidoso).
2. **Peso com degenerescência:** `w_i = g_i·exp(−ΔE_i/kT) / Σ_j g_j·exp(−ΔE_j/kT)`, `g_i` = `cre_members` do CREST. Ignorar `cre_members` subestima o mínimo (neutro: 1,2 % em vez de 8,5 %) — erro silencioso em qualquer média feita sobre saída do CREST. Energia livre do ensemble: `G_ens = −kT ln Σ g_i e^(−G_i/kT)`. `filter_boltzmann_population.py` implementa o corte.
3. **Re-rank DFT barato:** r2SCAN-3c/def2-mTZVP (`setup_r2scan3c_template.py`, `job_r2scan3c_optimize.sh`). A base é **def2-mTZVP atribuída à mão** no `define` (`b all def2-mTZVP`; o nome do método como "apelido" de base não faz nada); `$rij` explícito antes de `$end`; D4 e gCP entram sozinhos no runtime. Triagem de otimização: **cap de ciclos** (`jobex -c 10`) — moléculas com prenilas não disparam o critério formal de gradiente mesmo com ΔE ~1e-6 Ha; isso é para ranking, **não** para produção. SMP: `PARA_ARCH=SMP`, `PARNODES=8` (~17–25 s/ciclo p/ 46 átomos).
4. **r2SCAN-3c não faz IR nem UV** neste build (`Invalid value of nfun (53) in <mgga_r2>`; só falha ~25 min dentro do `aoforce`). Triagem de propriedades: PBE0/def2-SVP RI-J+RI-K (`setup_pbe0_svp_template.py`, `job_pbe0_ir_uvvis.sh`) sobre a geometria r2SCAN-3c — não reutilize a base def2-mTZVP no RI-K (auxbasis inutilizável). Teste "parcial" que passou por vários estágios **não** prova capacidade: deixe rodar até o estágio em questão.
5. **Rótulos de produção** = HSE06-D3(BJ)/def2-TZVP (mesmo nível do Paper 1): `job_hse06_labeling*.sh`, `fanout_*_jobs.py`, `select_active_learning_subset.py`. Camada A tem modos imaginários em ~100 % (geometria r2SCAN-3c × Hessiano PBE0) → é triagem; espectro de produção sai do HSE06 rotulado.
6. **Soma sobre estados:** não compare energia absoluta entre cargas diferentes (ver `thermo-pka.md`).

## Lição central: o corte do ensemble deve ser feito no solvente do observável

Para ânions de carga localizada (fenolato, dianião), o ranking dos confôrmeros é governado pela **solvatação**, não pela energia em gás (spread gás HSE06 ≈ 0,2 kcal/mol vs. solvatação COSMO 0,7–1,25). Conformeros fora do corte de 95 % em vácuo ficaram 1,7–3,3 kcal/mol mais bem solvatados que todos os do conjunto. E o ranking **GFN2/ALPB foi anticorrelacionado** com r2SCAN-3c/COSMO para B (ρ = −0,43) e D (−0,21) → o filtro semiempírico só amostra; o **corte decisivo é DFT/COSMO single-point em todos os confôrmeros**.

Plano em estágios: (W1) CREST/GFN2/ALPB ewin 8 → (W2) piloto de relaxação em solvente → (W3) r2SCAN-3c+COSMO SP em todos, população c/ degenerescência (95–99 %), reotimização dos sobreviventes e união por RMSD com os já calculados (`job_water_tier2_*.sh`, `job_water_reopt.sh`) → (W4) HSE06 + COSMO SP e `freeh` só no necessário → G_ens. Publicar **vácuo e água** lado a lado.

## Auditoria estatística do ML em N pequeno (protocolo congelado — reusar, não re-derivar)

Documento: `feature_selection_protocol.md` (neste repo).
- **Baseline "média dos outros" dá ρ_Spearman = −1 exato por álgebra do LOO** → "ótima correlação" inicial era artefato. Sempre comparar contra ele; **não usar ρ nem MAE/RMSE como figura de mérito**.
- Métrica: `Q²_LOO = 1 − Σ(e_i/(1−h_ii))² / Σ(y_i − ȳ)²` (PRESS fechado do OLS) + **teste de permutação ≥ 500** (usamos 1000–2000).
- Resultados negativos são mantidos e reportados.
- Fora da faixa de treino = "EXTRAPOLATION" (`apply_b1_model.py`); não extrapole (ex.: mon.B treino 0,0008 Å).
- sTDA reordena estados e pode pôr estado escuro espúrio abaixo do brilhante: **S1 por rank/energia está errado**; casar por caráter orbital (offset occ−HOMO, virt−LUMO do HSE06), e entre candidatos com coef ≥ 0,3 escolher **maior f**. Reportar a taxa de mismatch (8,3 %, IC Wilson 2,9–21,8 %) como limite de confiabilidade, não como erro gaussiano.
- Antes de usar GFN2 como baseline de uma propriedade, rode o "gate zero": comparar com o DFT barato por Spearman num subconjunto rotulado pequeno.

## Armadilhas específicas

- `std2 -xtb` morto (xtb ≥ 6.6 não gera `wfn.xtb`) → usar Molden de r2SCAN-3c. `std2` trunca/renumera o espaço ativo por rodada e conforme `-ax`; HOMO local = linha `oMOs in TDA: N`.
- `setup_population_job.py` reaproveita `mos` do dir de origem (nível HSE06 nos rotulados): Bader de confôrmeros só-r2SCAN-3c exige `ridft` HSE06 antes (~0,27 núcleo-h).
- Regex dos estados do `escf.out`: grupo 3 = eV, grupo 7 = f (comprimento). `$soes a 10` é pouco para bandas brilhantes altas.
- Bader/SEN usam `mos` HSE06, não r2SCAN-3c.
- Lotes de confirmação escf-only HSE06 ≈ 7,8 núcleo-h/confôrmero; `cosmo ridft` ≈ 0,52 núcleo-h/confôrmero; reotimização em água ≈ 3,7 núcleo-h/confôrmero (estimativa).
