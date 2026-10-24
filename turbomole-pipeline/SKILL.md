---
name: turbomole-pipeline
description: Pipeline completo e regras duras para iniciar e conduzir um estudo em TURBOMOLE (DFT/TD-DFT/IR/Raman/DOS/Bader/SEN, funil de confôrmeros CREST→r2SCAN-3c→HSE06, termodinâmica/pKa com COSMO) no cluster SLURM (access/coaraci). Use SEMPRE que o usuário for começar, planejar, retomar ou depurar um estudo em Turbomole — menções a define, coord, control, ridft, escf, aoforce, jobex, dscf -proper, HSE06, def2-TZVP, TD-DFT, Bader, DOS/PDOS, NTO, freeh, cosmoprep, CREST, confôrmeros, "novo estudo/molécula em turbomole", "rodar no cluster", "sbatch", ou quando um output do Turbomole "terminou" suspeitamente rápido — mesmo que ele não peça a skill pelo nome.
---

# Pipeline TURBOMOLE

Fluxo reaproveitável de **geometria → cálculo → extração → figura** para qualquer molécula. O que muda entre estudos é só o que está entre `<...>`; nunca cole placeholder literal num comando.

**Por que esta skill existe:** cada regra abaixo foi descoberta por um erro real (jobs que "terminavam" em 0 s, `control` truncado, dados salvos sem `$pop`). O custo de repetir um erro aqui é horas de cluster ou um resultado inválido que parece válido. Leia as regras duras antes de submeter qualquer coisa.

> ➡️ **MANUAL OFICIAL — consulte SEMPRE antes de adivinhar:** `references/Turbomole_Manual_8-0.md` (TURBOMOLE 8.0, ~16 mil linhas; versionado neste repo, vem no `git pull`). Para buscar novos métodos, keywords ou resolver qualquer problema/erro, **primeiro `grep -n` nele** (nunca ler inteiro): `grep -n -i "<keyword>" ~/skills/turbomole-pipeline/references/Turbomole_Manual_8-0.md` e `sed -n 'A,Bp'`. Âncoras: MD/frog `## 25.2.30 Keywords for Module frog`, `## 5.6 Molecular Dynamics`, surface hopping `## $surface\_hopping`, jobex `## 5.1.1 Options`, NAC `## 8.4.11 State-to-state`. O manual é 8.0; o cluster `access` roda 7.8.1 — conferir se a keyword existe na versão instalada.

## 0. Regras duras (do usuário — não renegociar)

1. **Estime o custo (núcleo-h) e REPORTE antes de submeter** qualquer coisa além de poucos minutos de CPU. Estimativas iniciais estiveram 20–40× baixas para moléculas com rotores (metilas/OH/prenilas) — pecar para cima; âncoras em `references/gotchas.md#custos`.
2. **Nada pesado no login node.** Valide pequeno e escale por `sbatch` (job array `--array=1-N%25`, script lê `$SLURM_ARRAY_TASK_ID`).
3. **Não decida mudança de arquitetura/nível de teoria sozinho** — reporte e pergunte.
4. **Valide por TEXTO, nunca por exit code.** `freeh`, `ridft`, `aoforce`, `escf` retornam 0 com "ended abnormally". Estágio com tempo ≈ 0 s = falhou. `sacct` COMPLETED também não prova nada: conte os marcadores (`GEO_OPT_CONVERGED` vs `GEO_OPT_FAILED`) por diretório. Grep: `"ended normally"`, `"all done"`, e ausência de `"ended abnormally\|did not converge"`.
5. **Jobs só sob `/home/rramos/work_turbomole/...`** (FS compartilhado). `/tmp` e o scratchpad do Claude não são vistos pelos nós — o job morre em 0 s sem `job.out`. Listas de jobs de array: caminho absoluto no FS compartilhado.
6. **Scripts novos:** inglês, `argparse`, modulares, sem hardcode, docstring com `Usage:`, rodáveis a partir da pasta do cálculo; testar antes de entregar. Ficam em `~/work_turbomole/scripts/` (repo git).
7. **GATE DE ESTABILIDADE DA FUNÇÃO DE ONDA (obrigatório antes de qualquer propriedade).** Metal de transição, camada aberta, singleto de gap pequeno (HOMO-LUMO < ~1 eV) ou qualquer sistema cujas cargas/spin/espectro serão reportados: rodar o teste de instabilidade + broken-symmetry (`references/stages.md` §1c) **numa cópia do `GEO_OPT_CONVERGED`** e gravar `.stages/STABILITY_OK` (E_restrito, E_BS, ΔE, ⟨S²⟩). Sem esse arquivo, `escf`/`aoforce`/NumForce/`dscf -proper`/Bader/cargas **não rodam e nada é reportado** — resultado sem o gate é provisório. Se o BS ficar abaixo do restrito (ΔE < −1e-5 Eh) ou o UHF estiver instável, a solução do estado fundamental mudou: geometria, frequências, população e espectros **são refeitos** a partir dela. Dispersão grande entre Mulliken/Löwdin/NPA/PABOON é sintoma a investigar com este gate, não só diferença de método.
8. **Nunca comparar energia absoluta entre estados de carga diferente** sem ciclo termodinâmico de referência.
9. **BENCHMARK DE FUNCIONAL ANTES DO PLANO (molécula nova).** Todo plano de estudo para uma molécula nova começa por um benchmark de funcional (precisão contra experimento/referência alta + custo medido), com veredito **separado** para estado fundamental e estado excitado. Proibido escolher o funcional por "é o que o grupo está acostumado" (HSE06 do Paper 1 incluso) — o nível do Paper 1 só é default quando o objetivo é comparar com o Paper 1. Protocolo, candidatos e armadilhas: `references/functional-benchmark.md`. O resultado (tabela de erros + núcleo-h + escolha) vai para a nota do projeto no cofre e a escolha final é do usuário (regra 3).

## 1. Intake — perguntar/confirmar antes de montar qualquer coisa

| Item | Por quê |
|---|---|
| Molécula, carga, multiplicidade | UHF muda `$scfinstab` (`urpa`, não `rpas`) e a ocupação no `define` |
| Objetivo (quais propriedades: UV, IR, Raman, DOS, Bader, SEN, NTO, pKa…) | define quais estágios entram e o custo |
| Nº de átomos e rotores flexíveis | decide se precisa de funil de confôrmeros e dá o fator de custo |
| Nível de teoria | molécula nova → **benchmark de funcional primeiro** (regra 9, `references/functional-benchmark.md`); nível do Paper 1 só se o objetivo for comparar com o Paper 1; mudar só com aprovação |
| Máquina/versão | `access` (GridUNESP, SLURM, TM 7.8.1 em `~/software/TURBOMOLE`); `coaraci` (nó inteiro, 48 núcleos/nó, TM 8.0.1 instalado e só smoke-testado) |
| Comparabilidade | se o resultado será comparado ao Paper 1, use exatamente seus parâmetros |

### Nível de produção (Paper 1, verificado no `control`)
`functional hse06` · `gridsize m4` · `$rij` + `$senex` · `$scfconv 8` · `$denconv 1d-7` · `$disp3 bj` (D3(BJ)) · base def2-TZVP · `$statpt`: `threchange 1.0d-7`, `thrmaxgrad 5.0d-4`, `thrrmsgrad 2.0d-4`, `thrmaxdispl 5.0d-4`, `thrrmsdispl 2.0d-4` · otimização em Cartesianas (`$optimize cartesian on`), `jobex -c 800` (o cap padrão do `jobex` é 100; prenilas/rotores precisam de ~100–800).
Referência de custo (artepilina C, 46 átomos, 16 núcleos SMP): `aoforce` ≈ 1 h, `ridft` reconvergência ≈ 1 min.

Regras de funcional (detalhes em `references/gotchas.md`): HSE06 → `senex`; PBE0/B3LYP → RI-K (`$rik`, menu `rijk`/`jkbas` do `define`); CAM-B3LYP rejeita RI-K → `senex`; B3LYP = `b3-lyp`, CAM-B3LYP = `cam-b3lyp`; **r2SCAN-3c não faz `aoforce` nem `escf`** neste build (meta-GGA) — para IR/UV use PBE0/def2-SVP (triagem) ou HSE06 (produção).

## 2. Fluxo

```
xyz ──► coord (xyz_to_coord.py) ──► define (templates setup_*_template.py)
   │
   ├─ molécula nova ─► Benchmark de funcional (references/functional-benchmark.md) ─► usuário escolhe
   │
   ├─ molécula rígida/pequena ─► Estágio 1 direto
   └─ flexível (rotores) ──────► Funil de confôrmeros (references/conformer-funnel.md)
                                   CREST/GFN2 → peso×degenerescência → r2SCAN-3c → HSE06
Estágio 1  jobex → ridft/escf/aoforce/dscf -proper  (references/stages.md)
Estágio 2  parsers → datasets .dat/.csv            (references/scripts-map.md)
Estágio 3  figuras                                  (skill `turbo_plot`)
Termodinâmica / pKa (opcional)                     (references/thermo-pka.md)
```

### Estágio 0 — geometria
`python ~/work_turbomole/scripts/xyz_to_coord.py --xyz mol.xyz --output coord` (Å → Bohr, símbolos minúsculos, `$coord`/`$end`; recusa sobrescrever sem `--force`). Sem RDKit/OpenBabel na base: moléculas pequenas = xyz escrito à mão e deixar o `jobex` refinar.

### `define` — sempre via template, nunca à mão
Use os `setup_*_template.py` (automatizam o `define` via pexpect/PTY): `setup_hse06_tzvp_template.py`, `setup_hse06_opt_template.py` (opt tight Paper 1), `setup_r2scan3c_template.py`, `setup_pbe0_svp_template.py`, `setup_gw_bse_template.py`, `setup_metal_complex_template.py`. Heredoc cego no `define` entra em loop infinito de menu; resetar `control/basis/auxbasis/mos` a cada tentativa. Depois confira o `control` à mão contra a lista do Paper 1.

### Estágio 1 — cálculos (resumo; comandos completos em `references/stages.md`)
0. **Gate de estabilidade/broken-symmetry (regra 7)** — antes de otimizar caro e antes de qualquer propriedade; para metal-complexos é o primeiro passo no `control` de partida.
1. `jobex -c 800` → exigir `GEO_OPT_CONVERGED`. Cap baixo (`-c 10/40`) só em triagem descartável; reotimização que alimenta G/pesos/espectro é produção. Se atingir o cap (`GEO_OPT_FAILED`): `rm GEO_OPT_FAILED not.converged` e reexecutar — continua da geometria atual; o estado sobrevive a `scancel`/TIMEOUT.
2. `ridft` (SCF) → `ridft -proper` (cubo p/ Bader) → Bader → **restaurar `control`** → `ridft` apertado.
3. `escf` (TD-DFT, `rpas`, `$soes a <N>` = **contagem**), `aoforce` (IR; checar imaginárias), `dscf -proper` com `$pop` (Mulliken/SEN).
4. Opcionais: DOS/PDOS, Becke/SCPA (Multiwfn), GW-BSE, NTO/HOMO-LUMO cubos, Raman.

Antes de seguir ao Estágio 2: `HOMO-LUMO Separation` em `proper.out`; `tail ACF.dat` (elétrons integrados ≈ Z total); sem frequência negativa em `vibspectrum`.

## 3. Armadilhas que mais custam (as demais em `references/gotchas.md`)

- **`dscf`/`ridft` consomem `$pop`** do `control`. `sed 's/^\$pop.*/…/'` falha em silêncio na 2ª chamada e o `dscf` roda sem população/`dos`. Use o helper `set_pop` (insere antes de `$end` se não existir) — em `references/stages.md`.
- **`sed '/^\$pointval/,/^origin/d'` apaga até o EOF** (não há `^origin`) e leva o `$end`. Em vez disso: `cp control control.pre_proper` antes do `ridft -proper`, restaurar depois do Bader. Sem restaurar, todo `dscf -proper` recalcula ~2,35 M pontos.
- **`$soes` é contagem** (`a 30`), nunca faixa (`1-30`). UHF: `$scfinstab urpa`.
- **`aoforce` pode "terminar normalmente" com hessiana estourada** (`**********` no `vibspectrum`; o `freeh` falha depois): grep por `*` antes do `freeh`, arquivar e refazer o `aoforce` (`references/gotchas.md`).
- **Estado sujo** (`$actual step …` após crash/walltime): `actual -r` antes de retomar; sintoma = aoforce/escf/pop "terminando" em 0–17 s.
- **`egrad` não aceita `$rik`** (out-of-memory no `escf_cc_setup`): só RI-J.
- **Banners "ended normally/abnormally" vão para STDERR** (`job.err`), não para o `.out`; sucesso no stdout = `"ridft : all done"`/`"escf : all done"`.
- **Locale pt_BR:** `printf "%.2f"` sai com vírgula e quebra nomes de pasta — use literais.
- **Monitores em background morrem** com a sessão: reconferir com `squeue`/`sacct` ao retomar.

## 4. Submissão SLURM (resumo)

`access`: partições `short` (1 d), `medium` (7 d), `long` (30 d), `gpu`; conta única `laser` (não passar `--account`). Paralelismo TM: `PARA_ARCH=SMP` + `PARNODES=$SLURM_NTASKS` (não somar `OMP_NUM_THREADS` por cima — dupla paralelização, o mesmo bug do CREST/OpenBLAS; no CREST use `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` e `-T`). `ulimit -s unlimited`. Modelo de script: `job_reference_compound_pipeline.sh` (retomável, valida cada estágio por texto). `coaraci`: nó inteiro por job → SEMPRE `par48-x`, `-N 1 --exclusive --mem=0`, 48 núcleos (nunca 16; erro real no job 1878811) → pedir 48 núcleos/nó e conferir walltime da partição (`par48-x` 3 d; sem 7 d em CPU).
**Arquivos `job.pbs` antigos são enganosos** (o cluster é SLURM; `qsub`/`qstat` não existem).

## 5. Ao fechar uma etapa

- Registrar no segundo cérebro (`/home/rramos/cofre`, `git pull` antes; notas condensadas por material; `active_session.md`; commit+push em marcos) — ver a nota `cofre_vault_workflow`.
- Lições novas de erro real entram em `references/gotchas.md` deste repositório, não só no cofre.
- Versão do TM e nível de teoria sempre explícitos no texto do paper/relatório. Citação obrigatória se usar Multiwfn/Molden2AIM: Lu & Chen, *J. Comput. Chem.* **2012**, 33, 580; Lu, *J. Chem. Phys.* **2024**, 161, 082503.

## Mapa de referências (leia só o que o passo atual exige)

| Arquivo | Quando abrir |
|---|---|
| `references/functional-benchmark.md` | molécula nova ou troca de funcional: protocolo do benchmark (GS × ES, custo, referências) |
| `references/stages.md` | executar/depurar um estágio (comandos, `set_pop`, DOS, NTO, GW, Raman, broken-symmetry) |
| `references/conformer-funnel.md` | molécula flexível; população de Boltzmann; rotulagem HSE06; ML delta-learning |
| `references/thermo-pka.md` | `freeh`, COSMO, ciclo de pKa, calibração por classe, microestados |
| `references/gotchas.md` | qualquer erro estranho; `define`/`cosmoprep`/`freeh`; custos; SLURM; versões TM |
| `references/scripts-map.md` | achar o script certo (layout `scripts/` × `scripts/scripts/`) |
