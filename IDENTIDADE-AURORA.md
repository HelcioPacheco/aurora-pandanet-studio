# Aurora — interface compacta

Direção revisada após o retorno do usuário: preservar o logo e priorizar uma ferramenta discreta, pequena e funcional. A identidade vem da composição, da marca e de poucos indicadores, sem grandes títulos ou ornamentos editoriais.

- Logo original de pedra e horizonte mantido; cobre concentrado na marca e nos indicadores de seleção.
- Verdana/Tahoma nos controles e nomes; fontes menores e sem espaçamento artificial. Serifada apenas no nome Aurora. Mantida a fonte local Tifinagh para seu alfabeto.
- Cabeçalho de 52 pixels, barra de sala compacta, lista de partidas em linhas e controles próximos à posição analisada.
- Fundos neutros contínuos nos modos claro e escuro; sem cartões decorativos ou molduras de cobre.
- Orientações, atalhos e explicações das ferramentas recolhidos no botão `?`. Seus elementos e atualizações permanecem disponíveis dentro da ajuda.
- Aviso permanente da demonstração removido da mesa: o estado continua no cabeçalho. Mensagens de erro e outros avisos continuam visíveis.
- Seleção das miniaturas indicada por um filete lateral; texto redundante “em destaque” removido.

Implementação em `static/aurora.css`, `static/aurora-mark.svg`, `static/index.html` e apresentação de estado em `static/app.js`. Sem dependências ou fontes externas novas.

Conferidos em prévia local com dados gravados: claro, escuro, abertura da ajuda, navegação por botão e teclado, retorno ao vivo e mosaico. Na janela de 1280 × 720, o tabuleiro mantém 300 pixels e as quatro miniaturas ficam inteiramente visíveis, sem transbordamento horizontal. As nove suítes JavaScript passaram. Outros tamanhos de tela ainda precisam de avaliação visual específica.

Capturas: `validacao/aurora-compacto-claro.png` e `validacao/aurora-compacto-escuro.png`. As capturas da proposta editorial anterior foram mantidas para comparação.

Direção visual incluída na distribuição v0.4.4.

## Refinamentos incluídos na v0.4.5

Botões mais finos e arredondamento discreto, tema Azul claro, tabuleiro principal maior, ferramentas por ícones com tooltip e skins Normal/Preto e branco. O mosaico OBS usa tamanhos iguais; o destaque mantém outros jogos nas laterais. A validação atual está em `NOTAS-v0.4.5.md`. As miniaturas ficam abaixo das ferramentas com rolagem própria, e as anotações mantêm suas cores também na skin preto e branco.
