---
name: cofre-sync
description: Atualiza o segundo cérebro (~/cofre) ao fim de sessão ou marco, garante que nenhuma pendência se perca e aposenta projetos concluídos. Use SEMPRE que o usuário disser "atualiza o cofre", "encerra a sessão", "fim de sessão", "registra isso", "concluímos o projeto X", "tira X do segundo cérebro", "limpa o cofre", "o que falta fazer", ou quando um projeto/estudo terminar (paper submetido, cálculo fechado) — mesmo sem dizer "cofre".
---

# cofre-sync — atualizar, não perder pendências, aposentar concluídos

Ferramenta: `python3 ~/cofre/tools/cofre.py {start|pending|check|retire}`. Regras completas: `~/cofre/PROTOCOL.md` (ler antes de escrever). Um fato mora em UM lugar.

## A. Atualizar (fim de sessão / marco) — nesta ordem
1. `git -C ~/cofre fetch && git -C ~/cofre pull` (conflito: linha a linha, nunca --theirs/--ours cego).
2. Para cada projeto tocado na conversa, editar a **nota-estado** `02_Memory/<codigo>/<proj>.md`:
   - sobrescrever estado/decisões/resultados obsoletos (com data); cronologia/diagnóstico longo → `_log/<proj>.md` (append) + 1 linha no índice da nota; `updated:` de hoje.
   - **Pendências:** varrer a conversa por "falta", "depois", "aguarda", "pendente", decisões adiadas, jobs a ler. Cada uma vira `- [ ] (user|ia) texto — AAAA-MM-DD` na seção `## Pendente`. As resolvidas viram `[x]`; as abandonadas `[~]` + motivo. Nunca deixar pendência só no chat.
3. `00_State/running_jobs.md`: job novo (id, máquina, projeto, dir, próximo passo); terminado → "Concluídos" (≤6; excedente → `04_Archive/jobs/AAAA-MM.md`). Só ativos ficam em "Rodando".
4. Lição de método/bug genérico → skill do código (`references/gotchas.md`, com data), não no cofre.
5. `python3 ~/cofre/tools/cofre.py check` — corrigir tudo que reclamar (tetos, status ausente, pendência sem data/envelhecida).
6. `git add -A && git commit && git push` (cofre e, se editou, `~/skills`).

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
