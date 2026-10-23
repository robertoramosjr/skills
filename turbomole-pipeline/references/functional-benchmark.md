# Benchmark de funcional (obrigatório em molécula nova — regra dura 9)

**Por quê:** no azobenzeno (2026) o HSE06 entrou no estado fundamental "por experiência do grupo" (artepillin-C) e só depois o benchmark mostrou CAM-B3LYP com erro médio 3× menor nos excitados — o que obrigou uma rodada nova de cálculos. O benchmark é barato (single points + 1 opt/aoforce por candidato numa molécula pequena); refazer o projeto não é.

## 1. Quando
- Molécula nova (ou classe nova de estado: excitado, aberto, metal) **antes** de montar o plano de produção.
- Exceção única: objetivo explícito de comparar com o Paper 1 → nível do Paper 1, declarado.

## 2. Candidatos (mínimo 4, de famílias diferentes)
| Família | Exemplos | Notas TM |
|---|---|---|
| Híbrido global | PBE0, B3LYP (`b3-lyp`) | `$rik` obrigatório (`define` → `rijk`/`jkbas`) |
| Híbrido blindado | HSE06 | `$senex` |
| Separado por alcance | CAM-B3LYP (`cam-b3lyp`), ωB97X-D/-V | **RI-K proibido** → `$senex`; `aoforce` com RSH: manual 8.0 diz "RSHs in all modules" (§ Notes about range-separated hybrid functionals, ~l.4259) — conferir no 7.8.1 com teste pequeno |
| Composto barato (só triagem/geometria) | r2SCAN-3c | sem `aoforce`/`escf` neste build |
Mesma base (def2-TZVP), mesma grade, mesma D3(BJ) em todos; GGA puro só se houver motivo.

## 3. O que medir — veredito SEPARADO para fundamental (GS) e excitado (ES)
**ES (TD-DFT, geometria fixa = FC):** energias verticais dos estados que importam (n→π\*, π→π\*, CT…) e forças do oscilador vs. máximos experimentais em fase gasosa (ou solvente com COSMO se a referência for em solução). Métricas: erro com sinal por estado + MAE. Conferir que o **caráter** (par de orbitais, NTO) é o mesmo entre funcionais antes de comparar números — ordem de estados pode trocar.

**GS (precisa de dados próprios — o benchmark de ES não decide o GS):** escolher ≥ 2 observáveis com referência experimental:
- geometria otimizada **com cada funcional** (comprimentos/ângulos chave vs. difração de elétrons em gás / raios X; declarar efeito de rede);
- energia relativa entre isômeros/confôrmeros (ΔE ou ΔH vs. experimento ou referência DLPNO-CCSD(T));
- IR: frequências escaladas (fator do CCCBDB para o funcional/base) vs. espectro experimental;
- −ε_HOMO vs. primeiro potencial de ionização vertical (PES/NIST) — útil para julgar DOS/alinhamento de nível.
**O gap HOMO–LUMO de Kohn–Sham não é observável**: não usar como critério de "acerto" (no azobenzeno ele quase dobra com CAM-B3LYP e até inverte o sinal cis/trans pela troca de ordem n/π).

**Custo (sempre medido, mesmos núcleos):** wall/CPU por módulo (`ridft`, `escf`, `jobex` por ciclo, `aoforce`) de `total wall-time` nos `.out`; converter em núcleo-h e projetar para a produção (nº de geometrias × estágios).

## 4. Critério de decisão (entregar ao usuário, regra 3)
1. Tabela: funcional × observável (erro com sinal, MAE) + núcleo-h por módulo + projeção da produção.
2. Se a diferença de precisão no GS entre candidatos for menor que a incerteza experimental, pesar **consistência**: um funcional único para GS e ES evita geometria de um funcional com excitação de outro, Wigner de uma hessiana com dinâmica em outra superfície, e corta uma rodada inteira de otimizações. Em dinâmica não adiabática o S0 da dinâmica **é** o do funcional do ES.
3. Registrar na nota do projeto no cofre: candidatos, tabela, referências bibliográficas exatas e a escolha do usuário com data.

## 5. Armadilhas já pagas
- **Referência experimental por isômero/estado**: o CSV do azobenzeno usou 2,82/3,90 eV para cis e trans; o correto era cis 2,92/4,68 e trans 2,82/4,12 eV (Maurer & Reuter 2011). Uma coluna `reference_eV` por isômero, com a fonte.
- Benchmark FC numa geometria de outro funcional (ex.: HSE06) é aceitável para triar ES, mas a produção reotimiza com o funcional escolhido — declarar.
- Script: `~/work_turbomole/scripts/scripts/prepare_functional_benchmark.py` (`--enable-rik` p/ híbrido global, `--enable-senex` p/ RSH).
- Molécula flexível: benchmark no confôrmero dominante do funil (r2SCAN-3c), não no xyz bruto.
