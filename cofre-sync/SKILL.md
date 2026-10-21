---
name: cofre-sync
description: Atualiza o segundo cérebro (~/cofre) ao fim de sessão ou marco, garante que nenhuma pendência se perca e aposenta projetos concluídos. Use SEMPRE que o usuário disser "atualiza o cofre", "encerra a sessão", "fim de sessão", "registra isso", "concluímos o projeto X", "tira X do segundo cérebro", "limpa o cofre", "o que falta fazer", ou quando um projeto/estudo terminar (paper submetido, cálculo fechado) — mesmo sem dizer "cofre".
---

# cofre-sync — atualizar, não perder pendências, aposentar concluídos

Ferramenta: `python3 ~/cofre/tools/cofre.py {start|pending|check|retire|capture|inbox|lint|experience|propostas}`. Regras completas: `~/cofre/PROTOCOL.md` (ler antes de escrever). Um fato mora em UM lugar.

## A. Atualizar (fim de sessão / marco) — nesta ordem
1. `git -C ~/cofre fetch && git -C ~/cofre pull` (conflito: linha a linha, nunca --theirs/--ours cego).
2. Para cada projeto tocado na conversa, editar a **nota-estado** `02_Memory/<codigo>/<proj>.md`:
   - sobrescrever estado/decisões/resultados obsoletos (com data); cronologia/diagnóstico longo → `_log/<proj>.md` (append) + 1 linha no índice da nota; `updated:` de hoje.
   - **Pendências:** varrer a conversa por "falta", "depois", "aguarda", "pendente", decisões adiadas, jobs a ler. Cada uma vira `- [ ] (user|ia) texto — AAAA-MM-DD` na seção `## Pendente`. As resolvidas viram `[x]`; as abandonadas `[~]` + motivo. Nunca deixar pendência só no chat.
3. `00_State/running_jobs.md`: job novo (id, máquina, projeto, dir, próximo passo); terminado → "Concluídos" (≤6; excedente → `04_Archive/jobs/AAAA-MM.md`). Só ativos ficam em "Rodando".
3b. **Inbox** (`cofre.py capture` e depois `cofre.py inbox`; captura automática de sessões do Claude e do Gemini): para cada linha, conferir `sacct -j <id>` na máquina indicada, levar o job/falha para `running_jobs` ou nota/plano (ou concluir que foi tentativa superada) e **apagar a linha**. Sessão "SEM cofre-sync" sem nada a registrar: apagar a linha.
4. Lição de método/bug genérico → skill do código (`references/gotchas.md`, com data), não no cofre.
5. `python3 ~/cofre/tools/cofre.py check` (já inclui o lint) — corrigir tudo que reclamar (tetos, status ausente, pendência sem data/envelhecida, links, `contradicts:` aberto, duplicata nota↔skill, memória local com fato de projeto → mover p/ cofre e deixar ponteiro). Achado de que o fato mudou: reescrever na nota e, se outra nota diz o contrário, `contradicts: [[x]]` até reconciliar.
5b. **Experiência** (quando o painel disser que está atrasada, ~14 d): `cofre.py experience`; para cada padrão real, 1 linha em `00_State/propostas.md` (`- [ ] AAAA-MM-DD → <skill>/<arquivo>: regra · evidência: hash data, hash data`), com ≥2 evidências. Mostrar ao usuário; `[x]` aprovado → copiar para a skill e apagar a linha; `[~]` + motivo fica (não repropor).
6. `git add -A && git commit && git push` no cofre **e sempre também em `~/skills`** (skills são código vivo: `git -C ~/skills status` a cada fim de sessão; se houver mudança, commit + push; se estiver limpo, confirmar que `origin/main` está em dia). Skill nova/alterada nesta sessão só vale em outras máquinas depois do push. Reportar os dois hashes. **Repos de scripts também:** `git -C <repo> status` em `~/work_turbomole/scripts`, `~/work_cp2k` (cp2k_scripts) e `~/work_vasp` (computational-materials-scripts); script de produção novo/alterado → commit+push (perguntar só se for WIP declarado). **Exceção `work_vasp`:** o GitHub guarda só `scripts/` (decisão do usuário, 2026-10-21) e o `grid_unesp` local tem histórico de dados — NUNCA `git push` dele; publicar por worktree a partir de `origin/grid_unesp` (receita em `02_Memory/meta/cofre-robustez.md`). Script fora do git já forçou reescrever o pipeline CP2K (2026-09-24).

## B. Aposentar projetos concluídos
1. `cofre.py check` lista `concluido` (prontos) e `start` lista `revisar` (a decidir). Para candidatos, **perguntar ao usuário** (AskUserQuestion): "X está concluído?". Não presumir.
2. Antes de aposentar: (a) pendências abertas → `[x]`/`[~]` com o usuário; (b) fato de método → skill; (c) resultado final que o paper/relatório cita → conferir que está na nota (ela vai para o arquivo, não some).
3. `status: concluido` na nota → `cofre.py retire <proj>` (dry-run: mostra jobs ainda listados e notas que o citam) → resolver avisos → `cofre.py retire <proj> --apply`.
   Efeito: nota + `_log` → `04_Archive/projects/<proj>/`, linhas removidas de active_session/global_index/running_jobs, 1 linha em `04_Archive/INDEX.md`. Nada é apagado (também no git).
4. Dados pesados do projeto continuam onde estão (fora do cofre); só o estado sai do caminho de leitura.
5. Rodar A.5–A.6.

## C. Higiene periódica (quando o usuário pedir "limpa" ou o painel mostrar muitas ENVELHECIDA)
- `cofre.py pending --user`: ler em voz alta as mais velhas e perguntar: continua / feita / abandonar.
- Projeto `pausado` há >60 dias: perguntar se vira `concluido` ou `revisar`.
- Notas >7 KB: mover cronologia para `_log/`.

## Regras
- Respostas curtas; citar `[[nota]]` afetadas. Reportar o que mudou: N pendências novas/resolvidas, projetos aposentados, tamanho do painel.
- Nunca aposentar com `[ ]` aberto sem `--force` explícito do usuário.
- `running_jobs` é memória: conferir `squeue`/`sacct` antes de mover job para concluído.
