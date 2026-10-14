# Regras globais (Roberto)

## Repositório de skills (`~/skills`, `git@github.com:robertoramosjr/skills.git`)
As skills `turbomole-pipeline`, `vasp-pipeline` e `cp2k-pipeline` vivem nesse repo e são expostas em `~/.claude/skills/` por symlink.
- **Início de QUALQUER sessão, em QUALQUER máquina:** `git -C ~/skills pull` (se `~/skills` não existir: `git clone git@github.com:robertoramosjr/skills.git ~/skills` e criar os symlinks conforme o `README.md` do repo) — outra máquina pode ter atualizado.
- **Fim de QUALQUER sessão (ou marco):** se alguma skill foi editada ou ganhou lição nova, `git -C ~/skills add -A && git -C ~/skills commit -m "..." && git -C ~/skills push`. Nunca deixar mudança sem commit/push ao encerrar.
- Conflito de merge: resolver linha a linha, nunca `--theirs`/`--ours` cego.
- Conteúdo: método e armadilhas ficam nas skills; **estado de projeto** (status, jobs, decisões em curso) fica no segundo cérebro (`~/cofre`, mesmo protocolo de pull/commit/push).

## Quando acionar as skills
Acione a skill do código (Turbomole/VASP/CP2K) sempre que, ao trabalhar em um projeto, faltar algum detalhe de método, parâmetro, armadilha ou fluxo — antes de adivinhar. Elas têm prioridade sobre memória/suposição para esses detalhes.

## Segundo cérebro (cofre) — `~/cofre`, `git@github.com:robertoramosjr/cofre.git`
Vault multi-IA/multi-máquina com o **estado** dos projetos (Turbomole, VASP, CP2K). Regras binding completas e tetos em `~/cofre/CLAUDE.md`. Reestruturado em 2026-10-14 após auditoria: o protocolo antigo custava ~25 mil tokens por início de sessão (active_session 41 KB, notas de 45 KB) e crescia a cada sessão; o novo custa ~5 mil e tem tetos verificados por script.

**Camadas (ler só até onde a tarefa exige):**
- **T1, todo início de sessão que toca projetos:** `git -C ~/cofre fetch && git -C ~/cofre pull`; ler **só** `00_State/active_session.md` (≤5 KB, 1 linha/projeto) e `00_State/running_jobs.md` (≤4 KB). Parar aí.
- **T2, ao tocar um projeto:** só a nota-estado `02_Memory/<codigo>/<material>.md` (≤7 KB: escopo, decisões vigentes, resultados, pendências, armadilhas, índice do log).
- **T3, só sob demanda e nunca inteiro:** `02_Memory/<codigo>/_log/<material>.md` (cronologia; ler por `sed -n 'a,bp'` com o índice da nota), `03_Handoffs/`, `04_Archive/`, `_Sources/`. Achar por `ls 02_Memory/*/` e `grep -rli`, não por índice longo.
- Nunca ler `_log/`, handoff ou archive de ponta a ponta; nunca `cat` de pasta.

**Escrita (um fato mora em UM lugar, os outros só apontam):**
- Estado/decisão/resultado final do material → nota-estado (**sobrescrever** o obsoleto com data; não empilhar entradas datadas). Cronologia e diagnóstico detalhado → `_log/` (append) + 1 linha no índice da nota. Job ativo → `running_jobs.md`. Visão do dia → 1 linha em `active_session.md`. Método/bug genérico → skill.
- Bullets, sem prosa; frontmatter `id/type: state/deps/log/updated`.
- Tetos (conferidos por `~/cofre/tools/budget.sh`): CLAUDE.md 5,5 KB · active_session 5 KB · running_jobs 4 KB · global_index 3,5 KB · nota-estado 7 KB. Estourou → rotacionar (Progresso Recente >7 dias sai; concluídos >6 de jobs vão p/ `04_Archive/jobs/`; cronologia da nota vai p/ `_log/`).

**Fim de sessão ou marco:** atualizar nota-estado + linha de `active_session.md` (estrutura obrigatória: Objetivo Atual / Progresso Recente [x][/] / Próximos Passos / Arquivos Relevantes) + `running_jobs.md` (ao submeter/terminar); `tools/budget.sh`; depois `git add -A && git commit && git push`. Empurrar cedo, não só no fim — sessões já foram cortadas.
- **Handoff IA→IA** complexo (≤4 KB): `03_Handoffs/YYYY-MM-DD-<origem>-to-<destino>.md`. Nunca apagar handoffs. Nunca `git checkout --theirs/--ours` cego em `02_Memory/`; antes de editar, `git fetch` (outra máquina pode ter commitado).
- `running_jobs.md` é memória, não verdade ao vivo: conferir `squeue`/`sacct` na máquina listada antes de afirmar estado (se estiver em outra máquina, dizer isso).
- Respostas ao usuário curtas, citando as notas afetadas via `[[...]]`.
- O cofre guarda **estado**; método/armadilhas vivem nas skills (seção acima). Não duplicar uma coisa na outra.
