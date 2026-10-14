# Armadilhas, custos e ambiente

Cada item veio de um erro real (TURBOMOLE 7.8.1 em `access`, 2026-08→10). Se descobrir uma nova, **acrescente aqui** com a data.

Conteúdo: [define](#define-e-input) · [Funcionais/TD-DFT](#funcionais-e-propriedades) · [Estado e cascata](#estado-sujo-e-cascata) · [SLURM](#slurm-e-ambiente) · [Custos](#custos) · [Versões](#versões-do-turbomole) · [Newton-X/scan](#scan-relaxado-e-newton-x)

## define e input

- **Dois prompts em branco no início**, não um: "skip reading defaults from another control file" e depois "INPUT TITLE". Mandar só um desloca todo o resto e consome `a coord` como título → "NO ATOMS, NO MOLECULE" (que não é problema do formato do coord).
- Geometria (`a <file>`, `*`): responder `no` para coordenadas internas se o estudo é em Cartesianas (convenção do Paper 1).
- Trocar base: `b` → `all def2-SVP`; "change atomic attribute data" = `y`; 1 confirmação "skip to library" por elemento; 9× `d` (jbas/jkbas/cbas × c,h,n); mos antigos inválidos → `y` + `eht`. `$rik`/`$jkbas` **sobram** → `sed -i '/^\$rik/d;/^\$jkbas/d'`.
- Sessões abortadas do `define` escrevem parcial no disco; ele re-injeta `$drvopt/$forceupdate/...` sempre → filtrar. **Resetar `control`, `basis`, `auxbasis`, `mos` limpos a cada tentativa.**
- Automatizar `define`/`icinp`: **stdin via arquivo + `timeout`**, nunca heredoc cego; input curto → loop infinito de menu (milhões de linhas). Use `pexpect` com PTY (piping simples dá ordem de prompts enganosa). Contar prompts lendo o log completo; o nº varia com o estado do `control`.
- `$rij` tem de ser adicionado ao `control` explicitamente se o `define` não ligou; inserir **antes** de `$end` (o Turbomole ignora tudo depois). Sem ele: "Option $rij not found!".
- `$end` ou data group sumindo: edições manuais (`cat >>`, `sed`) devem ficar **antes** do `$end`.
- `escfrisprep -m ris`: exige `$rik` + `cbas`; troca aux basis por 1 s/átomo; backups `control_ris_backup`, `auxbasis_ris_backup`.
- Sem `RDKit`/`OpenBabel` na base: moléculas pequenas = xyz à mão; `xyz_to_coord.py` converte.

## Funcionais e propriedades

- **RI-K obrigatório para híbrido global** (PBE0/B3LYP) em `ridft`/`escf`: sem `$rik`, 1 iteração SCF > 3 min (HSE06 com `senex`: ~35 s). Habilitar via `define` (menu `rijk` → `jkbas`).
- **CAM-B3LYP rejeita RI-K** ("range-separated hybrids not possible with RI-K!") → `senex` (`define`: `senex` → `on` → `n` gradiente → `y` CPKS). SCF ~6 min + escf ~20 min single-thread.
- **`egrad` não aceita `$rik`** (nem com ris/TDA): `Cannot allocate array temporary - out of memory` em `escf_cc_setup_`; independe de `$maxcor`/`$rpacor`/mem. Só RI-J.
- Keywords: B3LYP = `b3-lyp` (hífen); CAM-B3LYP = `cam-b3lyp`; não há ωB97X-D (`wb97/wb97x` com `dftd3bj=0`, ver `parameter/DFT-functionals.xml`).
- TDA = `$scfinstab ciss`; RPA = `rpas` (toggle no menu `ex`; sair com `*` ×3 + `y` para denconv). UHF = `urpa`.
- `$soes` = **contagem** por irrep (`a 30`), nunca faixa `1-30` ("could not read number of excitations").
- `egrad`: estado seguido = `$exopt n` (senão o maior de `$soes`).
- `ridft -proper` só gera `td.cub` com `$pointval fmt=cub`; depois de gerado o grid explícito fica no `control` e faz **todo** `dscf -proper` recalcular ~2,35 M pontos (travou). `$pop` + `$pointval` juntos duplicam o cubo caro → `$pointval` em arquivo separado, injetado só após o `dscf -proper`. **Não** usar `sed '/^\$pointval/,/^origin/d'` (apaga até EOF e perde `$end`).
- Banners "ended normally/abnormally" vão para **STDERR**; stdout: `ridft : all done`, `escf : all done`. `aoforce`: `"aoforce ended normally"`.
- r2SCAN-3c: sem `aoforce`/`escf` (ver `conformer-funnel.md`). Base **def2-mTZVP** (não "mTZVPP"), atribuída à mão.

## Estado sujo e cascata

- `escf` morto deixa `$actual step escf` → `aoforce`/`dscf -proper` seguintes morrem com `CONTRL dead = actual step`, "terminam" em 0–17 s com exit 0. **Tempo de estágio ≈ 0 s = falha.** Fix: `actual -r`.
- `aoforce` morto por walltime deixa `$actual step force` → `actual -r` antes de retomar.
- Script que segue para escf/aoforce mesmo com `jobex` não convergido (só WARNING) produz resultados pós-jobex **inválidos** — sempre `exit 1` sem `GEO_OPT_CONVERGED`.
- `jobex` sem `-c` = **100 ciclos**. Geometrias vindas de VASP/substituição atômica precisam de `-c 1500`.
- `GEO_OPT_FAILED` (cap) é informativo: `rm GEO_OPT_RUNNING not.converged` e reexecutar.
- UHF (Cu): `rpas` → "NOT IMPLEMENTED FOR UHF" → `urpa`; o template detecta `$uhf` no `control`.

## SLURM e ambiente

- Jobs só sob `/home/rramos/work_turbomole/...` (nós não veem `/tmp` nem o scratchpad do Claude → morre em 0 s sem `job.out`/`job.err`).
- Listas de jobs de array: FS compartilhado, caminho absoluto, `sed -n "${SLURM_ARRAY_TASK_ID}p"`.
- `sacct` com exit `78:0`/`0:53` sem outputs = falha de início; checar arquivos (NFS atrasa).
- Login node: OOM/lento. Validar pequeno; escalar por `sbatch --array=1-N%25`.
- Partições `access`: `short` 1 d, `medium` 7 d, `long` 30 d, `gpu`; conta `laser` única. `coaraci`: nó inteiro por job (48 núcleos/nó, tarefas×threads = 48), partições `par48-x` (3 d), `par480-x`, `teste`, `gpu-x`; array desperdiça nó.
- Conda: função de shell `conda`, sem `mamba`. Módulos: `xtb/6.6.1`. Envs: `paper2_funnel`, `veusz_env`, `vasp_env` (rdkit/ase/povray), etc.
- Rodar `find /` estoura o timeout — limitar profundidade.
- Locale pt_BR: `printf "%.2f"` com vírgula → pastas erradas; usar literais / `LC_ALL=C`.
- Monitores em background morrem ao fim da sessão — reconferir com `squeue`/`sacct`.

## Custos

Âncoras medidas (estimar para cima; reportar ao usuário antes de submeter):
- 46 átomos, HSE06/def2-TZVP, 16 núcleos SMP: `aoforce` ≈ 1 h; reconvergência `ridft` ≈ 1 min.
- r2SCAN-3c/def2-mTZVP, 8 threads: 17–25 s/ciclo (~3–5 min p/ 10 ciclos).
- HSE06 com ~100 átomos (metal-complexos): ~1000 s/ciclo (RSH); PBE ~125–150 s/ciclo; PBE0 (RI-K) 8–18 **h**/ciclo → inviável; `aoforce` PBE Ni = 48 h, HSE06 estoura 3 d.
- Moléculas pequenas com rotores (2,6-DMP): ~12+ núcleo-h em 85–100 ciclos cartesianos — estimativa inicial de 0,5 estava 20–40× baixa. `aoforce` de ferulato estourou 3 h com 4 cpu.
- Walltime de 3 d estoura rotineiramente em `jobex` HSE06 e em `aoforce` de sistemas grandes.
- `cosmo ridft` ≈ 0,5 núcleo-h/confôrmero (46 átomos); escf-only HSE06 ≈ 7,8 núcleo-h/confôrmero.

## Versões do TURBOMOLE

- 7.8.1: `~/software/TURBOMOLE` (produção, NTO via `proper`/`dftnto`). 8.0.1: `~/software/TURBOMOLE801` (access) e `~/software/TURBOMOLE` + `~/software/turbomole_env.sh` (coaraci, user `roarj`) — **só smoke-test** (H2O ridft+egrad); não afirmar validada para produção, azobenzeno ou Newton-X (NX lê a versão do nome de `TURBODIR`).
- `tm2molden` pede 2 linhas em branco (nome + confirmação Y/N).
- O `job.pbs` antigo nas pastas é enganoso: o cluster é SLURM.

## Scan relaxado e Newton-X

- `scanprep`: `$constraints` `tors c5 n23 n24 c8 start= end= stepsize=`; auto-detecta `$soes` → `jobex -ex`. Sem `-c` = rotação rígida do ponto de partida (colide anéis p/ CNNC baixo). Com `-c`: `concatenated_scan.sh` (`dfne` re-roda `define` por passo; `continue` dentro da função pula o for → `cd` falho e execução continua na pasta pai). Retomar = script com `j='<último_ok>'` e `scan_list` reduzida.
- Newton-X 26a: `icinp` opção 1 (IC): 20 respostas (`1,,2,,N,,,,,,n,1,,3,,,2.1,,`) sem prompt "parallel" (não existe na 26a), sair com `3`; `initqp_input` velho pergunta "delete old" e desalinha; `turbomole.par` fica vazio; JOB_AD = template TURBOMOLE (control/basis/auxbasis/mos) e o NX adiciona `$exopt`/gradiente sozinho; prog `2.1` = TURBOMOLE TDDFT; `split_initcond.pl` → `initcond.pl` por pasta → `merge_initcond.pl` (refazer apaga `INITIAL_CONDITIONS`/`I_merged` antes); `system("clear")` em `title()` foi neutralizado; `initcond.pl` roda ridft+escf e **descarta `escf.out`** (dados em `TEMP/exspectrum`/`initcond.log`); sondar com `< /dev/null` cria lixo (`I1/I2`, `I_merged`). Detalhes: nota `azobenzeno-b1-surface-hopping` no cofre.

## Metal-complexos (Cu/Ni/Zn × PBE/HSE06/PBE0, 2026-09→10)
- Template não punha `$pop` no `control` → `dscf -proper` final sem Mulliken/SEN; fix: `$pop mulliken loewdin nbo paboon` e reinserir antes do `dscf -proper`.
- `urpa` para UHF (Cu doublet); `$pointval fmt=cub` obrigatório no template (senão Bader falha silencioso: `td.cub does not exist`).
- `jobex -c 1500` para geometrias vindas de VASP/substituição atômica (o gradiente cai monotônico; só faltava iterar).
- Sistemas de ~100 átomos: `aoforce` PBE ≈ 48 h; HSE06 estoura 3 d; PBE0 (RI-K) inviável (8–18 h/ciclo). Na coaraci pedir nó inteiro (48 núcleos) e retomar só do rabo (`job_resume_force_pop.sh`).
- Cubo `fmt=cub` perde caroço de átomo pesado (Ni-PBE 331,88 vs 334,00 e⁻): cargas de Bader de metais não confiáveis nesse grid.
