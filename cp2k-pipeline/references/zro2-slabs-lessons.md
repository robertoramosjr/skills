# Estudo de slabs de ZrO₂ (CP2K, access→coaraci) — decisões e lições

Estado detalhado do projeto fica no cofre (`02_Memory/cp2k/zro2.md`); aqui ficam as lições reutilizáveis para qualquer estudo de superfícies de um óxido.

## Escopo e produto
- Objetivo: γ(hkl) → Wulff → forma do cristalito **por plano de crescimento** (Winterbottom), com o **mínimo de cálculos**. Planos de literatura: m (1̄11),(111),(1̄01),(011),(110) (Christensen & Carter 1998; Piskorz 2011); t (101),(111),(001),(100),(110) (Piskorz 2012); c (111),(110),(100). A cúbica ficou de lado (metaestável; relaxa para t) até a dopagem com Y.
- Bulk de partida: CONTCAR do VASP define o *setting* dos índices (P2₁/c: (1̄11) ≠ (111)).

## Cortes (06_slab_cut)
- Só slabs **estequiométricos, apolares (cargas formais) e simétricos**; Tasker III→II por reconstrução (metade da camada externa movida um período). Ordenar por ligações quebradas/Å²; terminação `_1` = menos ligações quebradas.
- Auditoria dos slabs VASP antigos: fio (c-100_1), não estequiométricos, assimétricos/polares, duplicatas, planos faltando → descartados.
- 27 slabs em 13 planos; só as `_1` (13) para vácuo/γ inicial; depois terminações 2/3 para m e t.

## Parâmetros de produção
CUTOFF 600 / REL_CUTOFF 50 Ry; k = `ceil(dens/|a|)×ceil(dens/|b|)×1` com a densidade do bulk de cada fase (c 20,46 / t 18,10 / m 16,12 Å); vácuo 25 Å; GEO_OPT, `--no-dipole`; mixing α 0.2.

## Lições
1. **Dipolo:** `SURFACE_DIPOLE_CORRECTION` ligado por padrão fez 43/65 tarefas abortarem (exige vácuo mínimo); slab simétrico não precisa → `--no-dipole`. O erro contaminou o teste de vácuo.
2. **Vácuo:** necessário (célula periódica em XYZ); no GPW custa só grade. 11/13 slabs convergiram em 8 Å; os dois com salto em 20 Å eram ruído SCF (entropia eletrônica 0, grids idênticos). Decisão: 25 Å.
3. **Espessura:** `08_thickness_series.py` casa a *mesma terminação* por ligações quebradas/Å² + origem (não pelo índice) e pula duplicatas; `parse_thickness.py` (|Δγ| < 10 mJ/m², ajuste de Fiorentini–Methfessel). Conjunto mínimo = 1 ponto mais fino + 1 mais grosso por plano do Wulff.
4. **Cúbica instável:** o interior do slab c-(100) virou tetragonal (O deslocados ±0,34 Å); γ calculado contra o bulk cúbico fica subestimado. Opções: fixar camadas centrais, impor simetria ou tratar c só como referência.
5. **Resultado t com ressalva:** γ t-(100) 0,952 < γ t-(101) 1,080 contradiz a literatura; o slab (100) é o mais fino (24 át.) → testar espessura antes de publicar.
6. **Forma:** com essas γ, a adesão (β) domina H/D ≈ 1 − 0,5β; o plano altera face do topo e laterais, não H/D.
7. **Custos** (ssmp 1×48, coaraci): c 20–60 min, t 47–530 min, m 223–379 min por slab; 27 slabs ≈ 39 nós·h (8–117); só `_1` ≈ 16.
8. **Migração de máquina:** `slab_meta["bulk"]` gravou caminho absoluto do access → cair em `<fase>/bulk_vasp_CONTCAR.vasp`; sbatch roda cópia do script em `/var/spool` → `common.sh` precisa procurar em vários caminhos.
