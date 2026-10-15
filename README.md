# skills

Skills do Claude Code do Roberto (Turbomole, VASP, CP2K). Cada pasta é uma skill (`SKILL.md` + `references/`).

| Skill | Quando aciona |
|---|---|
| `turbomole-pipeline` | começar/retomar/depurar estudo em TURBOMOLE (DFT, TD-DFT, IR, DOS, funil de confôrmeros, pKa/COSMO) |
| `vasp-pipeline` | cálculos VASP PAW-PBE (convergência 2×/1.125×ENMAX, slabs, defeitos, datasets ML) |
| `cp2k-pipeline` | cálculos CP2K (CUTOFF/REL_CUTOFF 2D, k-mesh, CELL_OPT, bandas, PDOS, slabs, híbridos) |
| `cofre-sync` | atualizar o cofre ao fim de sessão, garantir pendências, aposentar projetos concluídos |
| `research-paper-writing` | redigir/revisar Abstract, Intro, Method, Experiments; fluxo de parágrafos; auto-revisão adversarial (terceiros: Master-cai/Research-Paper-Writing-Skills @77e7c2c, MIT) |
| `academic-figure-skill` | figuras científicas para Nature/Cell/Science (matplotlib/R, specs de revista, QA) (terceiros: TingxiYu/academic-figure-skill @1df9940; assets ~137 MB) |

## Instalação (por máquina)
```bash
git clone git@github.com:robertoramosjr/skills.git ~/skills
mkdir -p ~/.claude/skills
for d in ~/skills/*/; do ln -sfn "$d" ~/.claude/skills/$(basename "$d"); done
```
CLAUDE.md global (versionado aqui em `global/CLAUDE.md`):
```bash
[ -e ~/.claude/CLAUDE.md ] && [ ! -L ~/.claude/CLAUDE.md ] && mv ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak
ln -sfn ~/skills/global/CLAUDE.md ~/.claude/CLAUDE.md
```
Atualizar: `git -C ~/skills pull`. Regra de sessão (também no `~/.claude/CLAUDE.md`): `git pull` neste repo no início e commit+push no fim, como no cofre.

## Convenções
- Corpo do `SKILL.md` curto (regras duras + fluxo + mapa); detalhe em `references/`, carregado só quando o passo exige.
- Lições novas de erro real entram em `references/gotchas.md` (ou equivalente) da skill, com data.
- Estado de projeto (status, jobs, decisões em andamento) **não** entra aqui: fica no cofre (`~/cofre/02_Memory/<codigo>/<material>.md`). A skill guarda método e armadilhas; o cofre guarda "onde estamos".
