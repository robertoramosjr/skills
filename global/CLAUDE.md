# Regras globais (Roberto)

## Skills (`~/skills`)
- Início: `git -C ~/skills pull`. Fim: `git -C ~/skills status`; mudou → add/commit/push. Conflito: linha a linha, nunca `--theirs/--ours`.
- Faltou método, parâmetro ou armadilha → skill do código (`turbomole-pipeline`, `vasp-pipeline`, `cp2k-pipeline`) antes de adivinhar.
- Problema novo em TURBOMOLE: `grep -n -i` no manual `~/skills/turbomole-pipeline/references/Turbomole_Manual_8-0.md` (nunca ler inteiro) antes de testar no cluster; citar no plano o §/linha.

## Cofre (`~/cofre`): estado, pendências, jobs
- Início: `git -C ~/cofre pull && python3 ~/cofre/tools/cofre.py start`. Projeto indicado → `cofre.py start <proj>` e só isso; nunca ler estado, `_log/`, handoff ou archive inteiros.
- Coisa a fazer → `- [ ] (user|ia) texto — AAAA-MM-DD` em `## Pendente` da nota; nunca só na conversa.
- Fim, marco, "atualiza o cofre": skill `cofre-sync`. Regras de escrita: `~/cofre/PROTOCOL.md`.
- **COARACI = NÓ INTEIRO, SEMPRE (regra dura):** todo `sbatch` na coaraci leva `--partition=par48-x` (ou a da GPU), `-N 1 --exclusive --mem=0` e 48 núcleos (`--cpus-per-task=48` ou ntasks×threads=48). NUNCA 16/24/8. Conferir `#SBATCH` com `grep` antes de submeter e `scontrol show job` (NumCPUs=48) depois. Falha em 2026-10-24 (job 1878811, 16 cpus).
- Cluster: executar até o `sbatch` (custo antes), registrar no plano + `running_jobs`, encerrar a vez; nunca polling. Na volta: reler o plano, validar por texto.
- Precedência: pedido atual > CLAUDE.md > skill > nota do cofre > memória local do Claude. Fato de projeto vai para o cofre (o Gemini e as outras máquinas não veem a memória local).
- Um fato em um lugar só; `running_jobs` é memória (conferir `squeue`/`sacct`).
