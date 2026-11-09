# Renders 3D de cristal com defeitos (átomo fantasma + poliedro) — método

Caso de origem: Fig. 1 do paper 2 Ag2CrO4:Nd (`paper/Figures/vacancy_configs.eps`), 7 configurações Nd_Ag + 2V_Ag, feito em 2026-11-09 com refinamento do usuário em 4 rodadas. Script de referência: `scripts/plot_vacancy_configs.py` (copiar e editar `CONFIGS`, `COL`, `RAD`, caminhos). Estilo molecular (H/C/O) é outra coisa: `academic-figure-skill/references/structure-renders.md`.

## 0. Antes de escrever código
1. **Pedir/ler a referência do usuário** (regra da skill). Aqui: `Ag2CrO4/CONTCAR.eps`, render do VESTA (161 MB, bitmaplib). Converter para olhar:
   `~/.conda/envs/writing_env/bin/gs -q -dSAFER -dBATCH -dNOPAUSE -dEPSCrop -sDEVICE=png16m -r150 -sOutputFile=ref.png X.eps`, depois `PIL.Image.MAX_IMAGE_PIXELS=None` e `thumbnail` para ler.
2. **Medir da referência, não chutar:** (a) cor do corpo da esfera (pixel no quadrante inferior esquerdo, longe do realce); (b) **raio = diâmetro em px ÷ (px/Å)**, onde px/Å vem de uma aresta da célula de comprimento conhecido (c = 20,46 Å ≈ 34 px/Å) → Ag 0,56, Cr 0,50, O 0,30, Nd 0,73 Å. Errei a escala na 1ª tentativa (raios 1,5× grandes, figura "atulhada").
3. Definir o rótulo de cada configuração (nomenclatura de publicação: `research-paper-writing` §8) antes de renderizar.

## 1. Dados (do CONTCAR relaxado, nada à mão)
- **Sítio vacante:** atribuição ótima (`scipy.optimize.linear_sum_assignment`, distâncias com `ase.geometry.get_distances(pbc=True)`) dos Ag da estrutura relaxada aos Ag da célula-mãe sem vacância; os 2 Ag da mãe sem par são os sítios vacantes.
- **Tipo do sítio:** nº de O vizinhos na mãe (Ag1 octaédrico: 6, 5º O < 2,85 Å; Ag2 tetraédrico: 4). Confere com a Tab. S3 do paper.
- **Fantasma = centroide dos n O mais próximos do sítio na estrutura RELAXADA** (os vértices do poliedro são essas posições relaxadas, por isso a distorção aparece). A distância Nd–fantasma assim difere até ~0,3 Å da distância Nd–sítio da mãe (Tab. S3); não misturar as duas na legenda.
- Átomos de face: repetir na face oposta se a fração < 0,02 (como o VESTA). **Fantasma não leva imagem periódica** (aparecia como 3ª vacância); o poliedro pode sair um pouco da caixa; vértices O fora do conjunto desenhado ganham uma esfera de O.

## 2. Cena POV-Ray (render_env: `~/.conda/envs/render_env/bin/povray`)
- Vista: c horizontal, b vertical, a para dentro, giro 28° (vertical) e 14° (horizontal); câmera perspectiva a 1000 Å com `angle` (o `orthographic` falha neste build).
- Ligações: cilindros bicolores (cada metade na cor do átomo), r = 0,07 Å, cortes Ag–O 2,75, Cr–O 2,0, Nd–O 2,8 Å. Célula tracejada preta (segmentos de 0,7 Å alternados), fundo branco.
- **Cores entram em sRGB direto, SEM linearizar** (este POV-Ray não codifica gama na saída; medido: corpo renderizado = valor de entrada). Linearizar como no `render_structures.py` deixou tudo escuro e saturado.
- Luzes **sem sombra** (`shadowless`; sombras davam meias-luas pretas nas esferas, a referência não tem) e **à frente de todos os objetos** (z ≤ −500; os objetos da camada da frente ficam em z ≈ −80: luz atrás deles = esfera preta).
- **Brilho** (pedido do usuário): `finish { ambient 0.22 diffuse 0.78 specular 1.0 roughness 0.004 phong 1.0 phong_size 250 }`. `reflection` deixa o Ag granulado: não usar.
- **Camada da frente para poliedros e fantasmas:** átomos de Ag escondem o poliedro. Mover os objetos `FRONT_SHIFT`=80 Å em direção à câmera e **reescalar a parte lateral por (1000+w−Δ)/(1000+w)** (e os raios pelo mesmo fator) mantém a projeção idêntica e os põe por cima. O fantasma vai 4 Å mais à frente que as faces, senão as faces coloridas o tingem (azul sob creme virou verde).
- Poliedro: arestas (cilindros r 0,055) + faces `triangle` com `rgbt` (transparência 0,5), vértices de `ConvexHull` (octaedro, 12 arestas) ou todas as 6 arestas (tetraedro). Cores: creme `#F3E3B0` (arestas `#C8A24A`), fantasma azul-céu `#8FD3F4` (pedidos do usuário).

## 3. Composição e saída
- Um PNG por painel (POV-Ray, `+A0.1 +UA`; alpha→branco depois), montagem em matplotlib: 178 mm, 3 colunas (2 colunas → 286 mm de altura, não cabe), rótulo `a)` em negrito no canto sup. esq. e o rótulo da configuração no sup. dir., ambos com fundo branco sólido; **o último painel é a legenda** (esferas coloridas + amostra do poliedro + frase T/O), 10 pt, serif.
- Saída: `.png` 600 dpi e `.eps` com o PNG dentro (`png_to_eps` da `render_structures.py`, Flate), `.csv` com sítios e distâncias, `_panels/*.pov` (editáveis). Validar: `~/.conda/envs/writing_env/bin/gs -q -dSAFER -dBATCH -dNOPAUSE -sDEVICE=nullpage X.eps` (o login node não tem `gs` no PATH).

## 4. Roteiro de iteração que funcionou
1. Renderizar **1–2 painéis a 300 dpi** (`--only A,B --dpi 300 --out /tmp/..`), olhar, ajustar; ~40 s cada rodada.
2. Cortar (`PIL crop`) a região do defeito a 600 dpi para julgar brilho/cor.
3. Só então rodar os 7 painéis a 600 dpi direto em `paper/Figures/` e validar o EPS.
4. Trocar a legenda do `.tex` para a descrição real das cores (conferir que "light blue/creme" etc. bate com a figura).

## 5. Armadilhas
| Sintoma | Causa | Correção |
|---|---|---|
| Fundo preto no PNG | POV-Ray gera RGBA | colar sobre branco com a máscara alfa |
| Esferas pretas/escuras no objeto da frente | luz atrás da camada deslocada | luzes em z ≤ −500 |
| Meias-luas pretas nas esferas | sombras projetadas | `shadowless` |
| Poliedro/fantasma escondido por Ag | oclusão | camada da frente (§2) |
| Fantasma verde-acinzentado | faces coloridas sobre o fantasma | fantasma 4 Å mais à frente |
| Vacância "extra" na borda da caixa | imagem periódica do fantasma | sem imagens para fantasmas |
| Estrutura atulhada | raios errados | medir na referência (§0) |
| Cores escuras/saturadas vs referência | linearização sRGB | hex direto |
| Figura de 286 mm de altura | 2 colunas × 4 linhas | 3 colunas |
