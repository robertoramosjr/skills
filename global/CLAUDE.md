# Regras globais (Roberto)

## Skills (`~/skills`, `git@github.com:robertoramosjr/skills.git`)
- Início de sessão: `git -C ~/skills pull` (sem o diretório: clonar e criar symlinks conforme o README do repo). Fim: sempre `git -C ~/skills status`; havendo mudança, `add/commit/push` (a skill `cofre-sync` cobra isso). Conflito: linha a linha, nunca `--theirs/--ours` cego.
- Acione a skill do código (`turbomole-pipeline`, `vasp-pipeline`, `cp2k-pipeline`) quando faltar método, parâmetro ou armadilha — antes de adivinhar. Método fica nas skills; estado no cofre.

## Cofre (`~/cofre`): estado, pendências, jobs — protocolo em camadas (reestruturado 2026-10-14)
- **Início de sessão (qualquer máquina):** `git -C ~/cofre pull && python3 ~/cofre/tools/cofre.py start` (painel de ~300 tokens). Quando o usuário indicar o projeto: `cofre.py start <projeto>` (nota-estado + jobs + pendências) e **só isso**. Não ler active_session, running_jobs, `_log/`, handoffs ou archive inteiros; nunca `cat` de pasta. Detalhe de log: `sed -n` pelo índice da nota.
- **Pendências:** toda coisa a fazer vira `- [ ] (user|ia) texto — AAAA-MM-DD` em `## Pendente` da nota do projeto; nunca deixar só na conversa. `cofre.py pending [--user]` lista tudo (marca ENVELHECIDA >14 d).
- **Fim de sessão/marco, "atualiza o cofre", "concluímos X":** skill `cofre-sync` (atualiza, confere pendências e tetos, aposenta concluídos, commit+push). Empurrar cedo. Regras completas para escrever: `~/cofre/PROTOCOL.md`.
- Um fato em um lugar só; `running_jobs` é memória (conferir `squeue`/`sacct`, dizer se está em outra máquina). Antes de editar o cofre: `git fetch` (outra máquina pode ter commitado). Handoffs imutáveis. Respostas curtas citando `[[nota]]`.
