# Armadilhas VASP e de dados

- **Cópia acidental de resultados:** `CaSv_struc2` e `CaBa_struc2` tinham `vasprun.xml` MD5-idêntico a `Bav_struc2`. Rodar `md5sum */vasprun.xml | sort | uniq -w32 -d` antes de montar tabelas.
- **Dois lotes incompatíveis** (`_struc` × `_OK`) divergindo 0,7–0,8 eV para estruturas com Ca (≈0,003–0,07 eV para vacâncias puras): comparar apenas dentro de um lote; documentar quando misturar.
- **Slab com normal inclinada + `IDIPOL=3`** não convergia o SCF (mono ZrO2): célula com c ⟂ superfície e ∥ z.
- **CONTCAR de FCC relaxou para bcc** (caminho de Bain) — a energia não era E_fcc; checar a rede após relaxar antes de usar como referência de fase.
- **Cálculo parcial lido como final:** `scancel`/TIMEOUT deixam CONTCAR/OUTCAR parciais; exigir `reached required accuracy`.
- **Nome de pasta mente** (`…_d3` com `IVDW=0`): conferir INCAR.
- **Pastas pesadas** (`HUBBARD_CORRECTION` ~93 G, `vasprun.tar.gz`): nunca versionar nem linkar; referenciar por caminho.
- **Apresentação/póster:** gerar números só a partir de arquivos reais; valores sem output no disco não entram (RMSE, EoS, MD).
- **Fila:** `(Priority)` não é erro. Arrays de milhares de pastas: usar `check_queue.py`, não `squeue` isolado.
- **VASP 6.6.1 na coaraci:** nó inteiro (48); `par48-x` 3 d; PBE ~125–150 s/ciclo, HSE06 ~1000 s/ciclo para ~100 átomos (CP2K/Turbomole, ordem de grandeza); `aoforce`/phonons grandes estouram 3 d.
- **pymatgen:** `Slab.is_polar()` sem oxidação = False sempre; `SlabGenerator` gira a rede por padrão; `get_tasker2_slabs()` falha em alguns Tasker III.
