# Armadilhas, custos e ambiente
> ➡️ Antes de adivinhar: `Turbomole_Manual_8-0.md` (mesma pasta) — `grep -n -i <keyword>`.

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
- **`$actual step` herdado por geradores de continuação (2026-10-16, azobenzeno SH):** ao montar um `control` novo a partir do de uma corrida que morreu (`ridft`/`dscf` com SIGSEGV), filtre também `$actual` (e `$last step`); senão a continuação morre em 2 s com `*** longjmp causes uninitialized stack frame *** ridft_omp terminated`. A mensagem do `jobex` ("missing input files … rerun define") é genérica e engana: olhar `job.last`/`jobex.out` e `grep '^\$actual' control`. *(correção do gerador em `scripts/prepare_tm_s0_continuation_v2.py`; confirmação em cluster pendente quando escrito)*
- Script que segue para escf/aoforce mesmo com `jobex` não convergido (só WARNING) produz resultados pós-jobex **inválidos** — sempre `exit 1` sem `GEO_OPT_CONVERGED`.
- `jobex` sem `-c` = **100 ciclos**. Geometrias vindas de VASP/substituição atômica precisam de `-c 1500`.
- `GEO_OPT_FAILED` (cap) é informativo: `rm GEO_OPT_FAILED not.converged` (guardar o `jobex.out` antigo) e reexecutar — o `jobex` continua do `coord` atual, não do zero. Scripts de array devem fazer isso sozinhos (modelo: `job_water_reopt.sh`).
- **Cap de triagem vazando para produção (2026-10-15, Paper 2):** a reotimização r2SCAN-3c/COSMO dos 343 sobreviventes em água foi submetida com `jobex -c 40` (herdado da lógica de triagem `-c 10`). `sacct` deu 343/343 COMPLETED, exit 0, mas **todos** com `GEO_OPT_FAILED` após 41 ciclos; energia ainda caindo ~0,1 kcal/mol a cada 5 ciclos (pior 0,3), comparável a kT → pesos de Boltzmann inválidos. Regra: **toda otimização cuja energia/geometria alimenta G, pesos ou espectro é produção → `-c 800`**; cap baixo só para ranking descartável. Ao "terminar", contar `GEO_OPT_CONVERGED`/`GEO_OPT_FAILED` por diretório — nunca concluir pelo `sacct`.
- **Medir quão perto do critério um job capado ficou** (decide se vale continuar): `energy` (ΔE nos últimos 1 e 5 ciclos, drift total ciclo 1→último) + bloco `CONVERGENCE INFORMATION` do `job.last` (quais dos 5 critérios estão `yes`). Em rotores prenila o gradiente máximo passa antes (~50–80 %) e os **deslocamentos** são os últimos a convergir. Pronto: `python3 ~/work_turbomole/scripts/reopt_convergence_report.py reopt/* [--csv out.csv]` (resumo por grupo: convergidos/capados, |ΔE5|, drift).
- **`aoforce` "ended normally" com hessiana corrompida (2026-10-15, ferulato ácido, HSE06/def2-TZVP, carga −1, 8 SMP):** CPHF convergiu, geometria sã, mas `hessian` com elementos ~5e2 (normal < 1), `vibspectrum` com `**********` nas frequências e o `freeh` "não parseou" (falha só aparece aí). A contagem de imaginárias por `awk` dá número sem sentido (27). Detecção: `grep -q '\*\{10\}' vibspectrum hessian` → falha (já em `job_reference_compound_pipeline.sh`). Fix: mover `aoforce.out hessian vibspectrum vib_normal_modes dipgrad` e saídas do freeh para `failed_aoforce_<data>/` e rodar `aoforce` de novo (o `jobex` convergido é reaproveitado). Causa raiz não identificada (a base −2, mesmo setup, saiu normal); resultado da reexecução `5272825` a registrar aqui.
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
- r2SCAN-3c/def2-mTZVP **+ COSMO**, 46 átomos, 8 SMP: **~35 s/ciclo** (21–30 min para 41 ciclos; COSMO encarece ~1,5× o vácuo) → ~3 núcleo-h por 40 ciclos/confôrmero. Partindo de geometria CREST/ALPB, 40 ciclos baixam ~2,3–2,6 kcal/mol e **não bastam**: orçar a reotimização em solvente para centenas de ciclos (343 conf. ≈ 1–3 mil núcleo-h).

## Versões do TURBOMOLE

- 7.8.1: `~/software/TURBOMOLE` (produção, NTO via `proper`/`dftnto`). 8.0.1: `~/software/TURBOMOLE801` (access) e `~/software/TURBOMOLE` + `~/software/turbomole_env.sh` (coaraci, user `roarj`) — **só smoke-test** (H2O ridft+egrad); não afirmar validada para produção, azobenzeno ou Newton-X (NX lê a versão do nome de `TURBODIR`).
- `tm2molden` pede 2 linhas em branco (nome + confirmação Y/N).
- O `job.pbs` antigo nas pastas é enganoso: o cluster é SLURM.

## Surface hopping nativo do TM (`frog`, `jobex -ri -ex -md`, 2026-10-16)

- **Classifique cada trajetória por TEXTO e em 4 estados, nunca só pela geometria final:** `hop_ok` (`event: hop` no `event.yaml` + S0 ≥ 20 fs), `no_hop` (rodou até o fim em S1), `died_S1` (sem salto e `jobex.out` termina em `ended abnormally`), `died_S0` (salto mas a continuação em S0 morreu cedo). Um `classify` que olha só o |CNNC| final rotula como "trans-like" trajetórias que nunca saltaram. Implementação: `scripts/summarize_sh_traj.py`.
- `mdmaster` `$nsteps` é reescrito pelo `frog` como **passos RESTANTES** (400 → 144 após 256 passos); não é teto. Não deduza tempo de simulação dele.
- Em diretórios JÁ rodados `coord` é sobrescrito a cada passo: para conferir a IC use o 1º quadro do `mdlog.1` ou um diretório virgem.
- Rendimento/fração de troca: denominador = só `hop_ok`; `no_hop`/`died_*` contados à parte (`scripts/aggregate_sh.py`, IC de Wilson).

## Scan relaxado e Newton-X

- `scanprep`: `$constraints` `tors c5 n23 n24 c8 start= end= stepsize=`; auto-detecta `$soes` → `jobex -ex`. Sem `-c` = rotação rígida do ponto de partida (colide anéis p/ CNNC baixo). Com `-c`: `concatenated_scan.sh` (`dfne` re-roda `define` por passo; `continue` dentro da função pula o for → `cd` falho e execução continua na pasta pai). Retomar = script com `j='<último_ok>'` e `scan_list` reduzida.
- Newton-X 26a: `icinp` opção 1 (IC): 20 respostas (`1,,2,,N,,,,,,n,1,,3,,,2.1,,`) sem prompt "parallel" (não existe na 26a), sair com `3`; `initqp_input` velho pergunta "delete old" e desalinha; `turbomole.par` fica vazio; JOB_AD = template TURBOMOLE (control/basis/auxbasis/mos) e o NX adiciona `$exopt`/gradiente sozinho; prog `2.1` = TURBOMOLE TDDFT; `split_initcond.pl` → `initcond.pl` por pasta → `merge_initcond.pl` (refazer apaga `INITIAL_CONDITIONS`/`I_merged` antes); `system("clear")` em `title()` foi neutralizado; `initcond.pl` roda ridft+escf e **descarta `escf.out`** (dados em `TEMP/exspectrum`/`initcond.log`); sondar com `< /dev/null` cria lixo (`I1/I2`, `I_merged`). Detalhes: nota `azobenzeno-b1-surface-hopping` no cofre.

## Metal-complexos (Cu/Ni/Zn × PBE/HSE06/PBE0, 2026-09→10)
- **Estabilidade/BS nunca foi rodada nos metal-complexos (apontado 2026-10-19):** Ni/Zn/Cu HSE06 foram otimizados, NumForce e `pop` concluídos sem teste de instabilidade/broken-symmetry; as cargas do metal divergem muito entre métodos (Cu: Mulliken 0,04 · Löwdin 0,12 · NPA 1,36 · PABOON 0,74/0,86), em parte por definição. Até o gate (SKILL regra 7) ser feito, geometria/freq/cargas deles são provisórias.
- Template não punha `$pop` no `control` → `dscf -proper` final sem Mulliken/SEN; fix: `$pop mulliken loewdin nbo paboon` e reinserir antes do `dscf -proper`.
- `urpa` para UHF (Cu doublet); `$pointval fmt=cub` obrigatório no template (senão Bader falha silencioso: `td.cub does not exist`).
- `jobex -c 1500` para geometrias vindas de VASP/substituição atômica (o gradiente cai monotônico; só faltava iterar).
- Sistemas de ~100 átomos: `aoforce` PBE ≈ 48 h; HSE06 estoura 3 d; PBE0 (RI-K) inviável (8–18 h/ciclo). Na coaraci pedir nó inteiro (48 núcleos) e retomar só do rabo (`job_resume_force_pop.sh`).
- Cubo `fmt=cub` perde caroço de átomo pesado (Ni-PBE 331,88 vs 334,00 e⁻): cargas de Bader de metais não confiáveis nesse grid.

## Vários cálculos no mesmo nó (coaraci, 2026-10-14)
- **`TURBOTMPDIR=/tmp` com nomes FIXOS** (`diff_densmat`, `olddensmat`): 2+ `ridft` no mesmo nó se contaminam (um UHF morreu com `forrtl severe (67)` por arquivo escrito por outro; um RHF de mesmo tamanho poderia ler errado em silêncio). Fix: `TURBOTMPDIR` privado por diretório de cálculo. `NumForce` já zera `TURBOTMPDIR` nos workers, mas **não** no `ridft` de referência.
- Estágios **idempotentes** (pular o que já foi validado por texto e é mais novo que `GEO_OPT_CONVERGED`; marcadores `.stages/{ALL_DONE,FAILED}`; `actual -r` e restaurar `control.pre_proper` no início) tornam fácil retomar após TIMEOUT. Quando o `aoforce` analítico não cabe em walltime: `NumForce -central` (retoma sozinho de `numforce/KraftWerk`). Dividir o nó entre cálculos com `taskset` em faixas disjuntas (3×16).

## Bader: resolução do cubo (Ni HSE06, 2026-10-14)
- m4/m5 é grid XC e **não** muda o cubo; espaçamento padrão de `$pointval fmt=cub` = 0,20 bohr (caixa = molécula ± ~3,5 bohr).
- Referência 334 e⁻: 0,20 original → 330,39 (Ni +2,47); 0,20 com origem deslocada → 335,22 (Ni +0,20); 0,10 → 333,36 (Ni +1,72). **O erro não é sistemático**: depende de onde o grid cai no pico 1s do caroço (all-electron). Carga de Bader de metal nesse cubo não é confiável; se 0,05 não convergir, Mulliken/Löwdin/NBO ou Multiwfn (bacia com refinamento atômico). Coaraci não tinha `bader` instalado.

## Multiwfn `DOS_curve.txt` com ≥2 fragmentos (2026-10-16, azobenzeno)
- A coluna 3 é o **OPDOS** (frag. 1×2, negativo por natureza), não um fragmento; valores negativos **colam colunas** (`29.468172-1019.275168`), então `split()` e `np.loadtxt` falham/leem errado. Ler por largura fixa (energia 10 chars + campos de 12): `parse_dos_scpa.py --opdos --energy-au --scale 10` (`--scale 10` = convenção do parser Becke, scale ratio 0,1). Sempre conferir soma dos fragmentos = TDOS.
- Becke e SCPA resolvem o PDOS negativo do Mulliken (`$pop mo dos` é Mulliken fixo no TM); Becke não separa s/p, SCPA sim.

## coaraci: GPU, arrays, espectros (2026-10-17, Ni-singleto HSE06)
- **Sem job array na coaraci** (usuário, 2026-10-17): cada tarefa do array ocupa uma vaga de fila e as filas dele são limitadas. Rodar **sequencial em 1 job** e auto-encadear com `--dependency=afterany:$SLURM_JOB_ID` (modelo: `job_metal_complex_trio.sh`). Isto vale para qualquer script novo na coaraci (vale também onde a regra 0.2 do SKILL.md fala em array).
- **aoforce em GPU** (`source ~/software/turbomole_gpu_env.sh`, fila `gpu-x`, 1 A30 + 16 núcleos): Ni HSE06 67 átomos, 3h07 (vs >3 d em CPU/NumForce); energia/vibspectrum iguais à CPU no Ni(CO)4 (fp32 e fp64). Rodar numa CÓPIA do diretório. Cu (UHF) em GPU ainda não validado.
- **Raman DFT**: `aoforce` só dá IR (coluna RAMAN do `vibspectrum` = regra de seleção). Intensidades: `egrad` com `$scfinstab polly` + `intense` (validado Ni(CO)4: 24 s). Antes de `egrad`, tirar `$scfinstab rpas`/`$soes` da cópia (senão `$scfinstab` duplicado). NÃO fazer diferenças finitas da polarizabilidade (342 pontos ≈ 63 h de GPU) — a rota analítica custa ≈ 1 aoforce.
- **`tm2molden`**: 1º prompt = NOME DO ARQUIVO DE SAÍDA (padrão `molden.input`), não o `mos`; responder com linhas em branco. Digitar `mos` nele pede para sobrescrever o próprio `mos`.
- **`vib_normal_modes`/`hessian`**: linhas de largura fixa (`i3 j2` + 5 valores; `535` = linha 5, bloco 35), logo `split()` quebra. Modos = deslocamentos cartesianos de norma 1; massa reduzida = Σ m·L². Polarizabilidade do `escf` (polly) em bohr³, tensor em "electronic polarizability :".
- **Multiwfn DOS em batch** (menu 10): `8` (eV) · `2` faixa+passo · `3` FWHM · `0` plota · `3` exporta `DOS_curve.txt`/`DOS_line.txt` · `0` · `-10`. Script: `scripts/tm_dos.py` (HOMO/LUMO e gap incluídos).
- **UV-vis**: o `exspectrum` só vai até o último estado do `$soes`; abaixo disso o espectro ampliado não é confiável (Ni: 30 estados, até 283 nm). `scripts/tm_spectra.py` (IR + UV-vis).
- Termoquímica: o Hessian da GPU basta para `freeh` (entrada em branco, 298,15 K, 0,1 MPa); sem imaginárias no Ni (menor modo 32 cm⁻¹).


- **2026-10-17 — `vib_normal_modes` é largura fixa** (componente cols 1-3, bloco de 5 modos cols 4-5): a partir do bloco 10 os campos se encostam (`  710`) e `split()` descarta a linha. Leitor antigo do `ir_mode_assign.py` lia só 45 modos (moléculas com >15 átomos); picos acima do modo 45 nunca eram rotulados. Corrigido; leitor novo valida 3N×3N. Figuras de IR geradas antes disso precisam ser refeitas.

## Validar `dscf -proper` por "dscf : all done" (2026-10-17, metal-complexos)
`run_metal_complex_stages.sh` marcou `.stages/FAILED` em Ni/Zn com `pop.out` válido: "ended normally" vai ao stderr, no stdout só `dscf : all done`. Qualquer `fresh_ok` sobre `.out` deve usar esse padrão; um FAILED falso derruba o sucessor do trio (round 2 abortou).

- (2026-10-19) SH nativo: `maxlog` do `mdmaster` ($log_history) NÃO controla os grupos de SH ($population_el, $prob_fssh, $sh_coeffs, $egradmon têm `maxlog= 256` no próprio control). Subir só o do mdmaster não evitou a morte dos trans no passo 256 (control truncado, 5/5). Teste de hipótese de log-rolagem tem de mudar TODOS os maxlog.
- (2026-10-19) SLURM COMPLETED ≠ trajetória boa: jobs de SH saem com exit 0 mesmo com SIGSEGV no S0; validar com `summarize_sh_traj.py` (status hop_ok). `$actual step ridft` residual não é a causa única do SIGSEGV pós-salto (gerador v2 ainda morre no 1º quadro de S0).

## SIGSEGV determinístico do `ridft` com COSMO numa geometria (2026-10-21, artepilina B c0026)
`jobex` morre com `forrtl: severe (174) SIGSEGV` em `vcl_ll_cos`/`vspdf_cosmo` (cavidade COSMO) e o jobex reporta só "ERROR in dscf step". Reproduz em serial e com `OMP_STACKSIZE=4G`, então NÃO é thread/stack/estado sujo: é a geometria exata do ciclo (já havia ocorrido no ciclo 49 do mesmo conformero). Correção que funcionou: ruído de ±1e-3 bohr em todas as coordenadas do `coord` (backup antes), `rm GEO_OPT_FAILED not.converged` e reenviar; E muda ~1e-5 Eh. Diagnóstico barato: `ridft` único em cópia (control/coord/basis/auxbasis/mos) via sbatch, 3–5 s por teste. Sempre ler `jobex.out` (o SIGSEGV está lá, não no `slurm_*.error` vazio).

## Formato de `vib_normal_modes` e G_térmica por xtb (2026-10-21, Paper 2)
- `vib_normal_modes` do `aoforce` é **largura fixa**: coordenada (i3), bloco (i2), até 5 valores por linha (5 modos/bloco, 3N linhas/bloco). Em 3 dígitos as colunas colam ("110" = coord 1, bloco 10): `split()` falha; usar `line[:3]`, `line[3:5]`, `line[5:]`.
- Fonte barata de G_térmica sem `aoforce`: `xtb mol.xyz --gfn 2 --chrg Q --bhess` (mRRHO de Grimme, funciona fora do mínimo xtb; o `--hess` puro pode dar imaginárias). `xtb` 6.6.1 vem em `$TURBODIR/bin/<sys>/xtb`. NumForce só tem níveis scf/ri/mp2/cc2/rirpa (manual §15 L8528); `freeh` é RRHO puro (L8520). Validar contra `freeh` HSE06 antes de usar (piloto Paper 2, `5292001`).
- `aoforce` HSE06/def2-TZVP, 46 átomos, 16 CPUs: 1 h 43–1 h 55 medidos (≈27–31 núcl-h); exige mínimo do MESMO nível (reopt HSE06 em gás antes se a geometria é r2SCAN-3c).

- 2026-10-21 (coaraci): `$gpgpu` no `control` faz o binário CPU abortar ("NO GPU FOUND", egrad ended abnormally em 3 s). Ao migrar uma cópia de dir GPU para CPU/par48-x: `sed -i '/^\$gpgpu/d' control` (feito em `job_raman_egrad_cpu.sh`). par48-x não tem GRES GPU: job com `gres/gpu` movido para lá fica `PENDING (BadConstraints)`.

- (2026-10-22) SH nativo, reinício de MD: `jobex -ri -ex -md` com `nextstep=ridft` e `$nsteps N` retoma bem uma trajetória curta (127→131 quadros, control íntegro; 7.8.1). O 1º `ridft` do passo dscf-like pode sair "ended abnormally" sem impedir os ciclos. Snapshot de 256 ciclos (todos os `maxlog`=256 cheios) trunca o control para ~173 linhas no 1º `egrad` mesmo com `ridft` manual e `nextstep=egrad`; rota, tamanho do control e versão (7.8.1/8.0.1) não influem. Nenhuma corrida passou do ciclo 255 com `maxlog`≠256 (rolagem não descartada).

## Espectros/DOS/estabilidade em metal-complexos (2026-10-22)
- **`exspectrum` com blocos anexados:** o `escf` acrescenta em vez de sobrescrever; o arquivo pode ter 2+ cabeçalhos `# Excitation spectrum` (geometria antiga + válida). `tm_spectra.py` soma tudo (curva dobra, estados repetidos). Conferir `grep -c "^# Excitation" exspectrum` e usar só o último bloco (`awk '/^# Excitation spectrum/{n++} n==K'`).
- **`tm_dos.py` em UHF:** o gap por `levels[nocc]` sobre α+β misturados é errado (Cu: 3,28 eV vs 2,505 eV real); `nocc` de camada fechada = nº de elétrons/2 (Zn 168, Ni 167: conferir `$closed shells`). Desde 2026-10-22 o script lê os níveis α/β do molden (gap por spin e global) e reconstrói o TDOS (o do Multiwfn em UHF não bate; no RHF a razão é constante 0,3133).
- **`freeh` fora do PATH** sem `source ~/software/turbomole_env.sh`; prompts `\n\n\nq`. Rodar em cópia (`thermo/freeh_<X>/`).
- **Gate de estabilidade:** manual §8.4.5 só documenta camada fechada (`$scfinstab singlet|triplet` + `$soes all 1`; `$start vector generation` gera MOs BS). `urpa` para UHF não está no manual (ainda não testado). Scripts: `setup_stability_test.sh` + `job_stability_test.sh` (repo `turbomole`).
