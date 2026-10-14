# Termodinâmica, COSMO e pKa

Aplicável a: ΔG de reação em solução, pKa/especiação, ensembles com cargas diferentes. Referência trabalhada: artepilina C (Paper 2). Scripts em `scripts/` (ver `scripts-map.md`).

## Ciclo

```
G_aq = E_el(HSE06/def2-TZVP, gás) + G_térmico(freeh) + G_solv(COSMO)
G_solv = E_COSMO(ε = 78,4, OC) − E_gás   (geometria CONGELADA do gás)
G(H⁺,aq) = −6,28 + (−265,9) = −272,18 kcal/mol   (Tissandier 1998; verificar a fonte ao citar)
pKa = ΔG_aq / (RT ln10)
```
Média por ensemble: `G_ens` com degenerescência CREST (e −T·S_conf como sensibilidade, não no resultado primário).

## Etapas e como cada uma falha

1. **`aoforce`** no geométrico convergido (`GEO_OPT_CONVERGED`). Imaginárias < −10 cm⁻¹ → investigar antes do `freeh`.
2. **`freeh`** — interativo, prompts nesta ordem: (1) nº de simetria "Hit RETURN" → RET; (2) fator de escala de frequência → RET; (3) faixa T/P → RET (298,15 K / 0,1 MPa), que **re-pergunta** → `q`. `chem.pot.` = correção térmica de G em kJ/mol, a somar à E eletrônica. **Rodar sempre em CÓPIA** (em-lugar escreve `$last step freeh` no `control`). Wrapper: `run_freeh_thermal_correction.py`. Exit 0 coexiste com "ended abnormally" → grep.
3. **`cosmoprep`** (~14 prompts): ε → `78.4`; 9× RET (refind, LR, RF equil., nppa, nspa, disex, rsolv, routf, cavity); amat → `*`; menu de raios → `r all b` depois `*`; output file RET; correlacionado RET(n). Wrapper: `setup_cosmo_job.py`.
   - **Bug:** amat `*` grava `amat file=*` em `$cosmo` e o `ridft` rejeita ("unknown keyword") → `sed -i '/amat file=\*/d' control`.
   - **Falha silenciosa (~1/40):** diz "ended normally" mas **não grava `$cosmo`** → `grep -c '^\$cosmo$' control` em cada diretório.
   - Com `pexpect` usando só `[EOF, TIMEOUT]` espera o timeout inteiro a cada passo (~1–2 min por `cosmoprep`) → rodar em background/SLURM.
4. **COSMO single-point:** `ridft` (custo ≈ 0,5 núcleo-h/confôrmero de 46 átomos).
5. **Soma:** `compute_pka_thermodynamic_cycle.py` (`compute_cycle`), `assemble_state_pka_thermo.py`. Fechamento do ciclo = 0 é identidade por construção, não validação.

## Calibração por classe de referência

O ciclo COSMO sem águas explícitas tem resíduo sistemático (−3,4…−4,5 unidades de pKa na artepilina C). Subtrai-se um **offset por classe** medido em ácidos de referência do **mesmo tipo de desprotonação/carga** (0→−1, −1→−2). Isto é calibração empírica — dizer assim, nunca "pKa de primeiros princípios".

- Pipeline de uma referência: `job_reference_compound_pipeline.sh` (jobex −c 800 → aoforce → freeh → COSMO → ridft; retomável; valida cada estágio por texto). Geometria: `setup_hse06_opt_template.py` com `$statpt` tight do Paper 1 — **mesmo nível** do alvo, senão o offset perde sentido.
- Resumo: `summarize_pka_calibration.py --refs pka_refs.csv --targets pka_targets.csv [--apply-sconf]` → offset médio ± desvio amostral por classe (N=1 não tem dispersão; nunca fingir). Propaga também a faixa experimental da referência separadamente da dispersão de classe.
- **Nomes no CSV não podem ter vírgula** (`2,6-…` quebra a linha → `26-dimethylphenol`).
- **Fonte dos pKa experimentais:** conferir em fonte primária ou no dataset IUPAC (Serjeant–Dempsey), nunca de memória; reportar T, força iônica, método. Constante aparente a I > 0 difere da termodinâmica (Debye–Hückel grosseiro: passo −1→−2 em I = 0,1 M desloca ~0,3–0,4 unidades) — documentar, não aplicar sem decisão do usuário. Se duas fontes divergem, rodar a calibração com as duas e reportar a faixa.
- Referências pequenas com rotores (metilas/OH) custam 20–40× a estimativa: 2,6-dimetilfenol ≈ 12+ núcleo-h em ~85–100 ciclos; walltime ≥ 12 h.
- Para saber se uma classe é homogênea é preciso N ≥ 3; com N = 2 reportar como "não distingue as hipóteses".

## Solvente e completude do ensemble (resumo)

- COSMO single-point em geometria de gás ≠ otimização em solvente; a relaxação r2SCAN-3c→HSE06 em gás deu ΔE ≈ −1 kcal/mol quase igual entre estados (δpKa ≤ 0,15) — hipótese de que o Estágio de reotimização HSE06 era necessário para o pKa foi **refutada**.
- COSMO tem spread 2,6–2,7× o do GFN2/ALPB nas solvatações de aníons (mesma ordem, r = 0,99–1,00) → a incerteza do modelo de solvente (~±0,3–0,5 pKa) é do tamanho do efeito da completude do ensemble. Reportar a faixa por modelo.
- Pares com dianião: baixa confiança (offset −1→−2 com N pequeno, COSMO subestima poliânions, poucos confôrmeros). Um gap implausível entre pKa(A→D) e pKa(N→B) deve ser **sinalizado, não explicado**.

## Microestados de uma molécula poliprótica

Enumere os sítios independentes e os estados (artepilina C: carboxila + fenol → neutro, monoânion A carboxilato [dominante], monoânion B fenolato [minoritário, [B]/[A] ≈ 5e−4], dianião; sem cátion em pH 0–14). Gere cada estado com `build_protonation_state.py`; rode o **mesmo** pipeline completo em todos, sem reaproveitar geometria entre estados. Especiação vs pH: `plot_speciation_vs_ph.py`; banda UV vs pH: `predict_uvvis_vs_ph.py` (previsão, não validação, até haver espectros vs pH medidos).
