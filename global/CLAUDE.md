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
Vault multi-IA/multi-máquina com o **estado** dos projetos (Turbomole, VASP, CP2K). As regras binding completas estão em `~/cofre/CLAUDE.md` — reler em caso de dúvida.
- **Início de QUALQUER sessão que toque nos projetos:** `git -C ~/cofre pull`; depois ler **só** `00_State/active_session.md`, em seguida `00_State/running_jobs.md` (onde cada job roda) e, se precisar localizar algo, `01_Indexes/global_index.md`. Abrir `02_Memory/<codigo>/<material>.md` somente quando estritamente necessário (divulgação progressiva: nunca ler todas as notas).
- **Escrita:** notas condensadas (bullets, sem prosa), frontmatter `id/type/deps`, nomes em minúsculo hifenizado por material em `02_Memory/turbomole|vasp|cp2k/`. Um material em dois códigos: uma nota canônica e um stub.
- **Fim de sessão ou marco:** atualizar `active_session.md` mantendo a estrutura obrigatória (Objetivo Atual / Progresso Recente [x][/] / Próximos Passos / Arquivos Relevantes) e `running_jobs.md` (job id, máquina, projeto, diretório ao submeter; mover para "Concluídos" ao terminar); depois `git add -A && git commit && git push`. Empurrar cedo, não só no fim — sessões já foram cortadas.
- **Handoff IA→IA** complexo: criar `03_Handoffs/YYYY-MM-DD-<origem>-to-<destino>.md`. Nunca apagar handoffs antigos. Nunca `git checkout --theirs/--ours` cego em notas de `02_Memory/`.
- `running_jobs.md` é memória, não verdade ao vivo: conferir `squeue`/`sacct` na máquina listada antes de afirmar estado (se estiver em outra máquina, dizer isso).
- Respostas ao usuário curtas, citando as notas afetadas via `[[...]]`.
- O cofre guarda **estado**; método/armadilhas vivem nas skills (seção acima). Não duplicar uma coisa na outra.
