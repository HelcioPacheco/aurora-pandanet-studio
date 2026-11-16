# Aurora Pandanet Studio 0.4.5

24 de outubro de 2026. Preserve a pasta `data/` ao atualizar.

- Botões mais finos e raio de 4 pixels; campos, painéis e janelas com cantos discretamente arredondados. Tabuleiros continuam quadrados.
- Terceiro tema, Azul claro. A preferência é restaurada ao abrir a página e sincronizada com a saída OBS. Os temas anteriores foram preservados.
- Tabuleiro principal da tela de operação ampliado e grafo mais estreito. As partidas acompanhadas ficam abaixo das ferramentas, em uma lista com rolagem própria. Rolar a lista preserva a posição da página e do grafo; escolher uma miniatura troca o jogo principal sem perder a rolagem da lista.
- Ferramentas em dez botões com ícones, tooltip traduzido e indicação da ferramenta selecionada. A seleção continua cancelando desenhos incompletos. Letras, números e liberdades mantêm o funcionamento anterior.
- Seletor de skin no cabeçalho: Normal ou Preto e branco. O modo monocromático usa fundo branco, linhas pretas e pedras lisas. As marcações mantêm a cor escolhida também no modo preto e branco, e o seletor de cor continua disponível. A numeração automática preserva o contraste com as pedras. O jogo e as anotações permanecem intactos. A escolha da skin persiste com a disposição da tela e acompanha miniaturas, mosaico e OBS.
- OBS em destaque: tabuleiro central ampliado e outras partidas nas laterais, sem repetir o jogo principal.
- OBS em mosaico: todos os tabuleiros com o mesmo tamanho, conforme a decisão mais recente do usuário. A grade usa a janela disponível e não mantém o limite antigo de 170 pixels. A alternativa com tamanhos diferentes foi removida.
- OBS usa resolução completa do desenho, evitando ampliar imagens pequenas. A reorganização responde a mudanças da janela, quantidade de jogos e modo, sem novas consultas periódicas ao servidor.

Validação: 80 testes Python e onze suítes JavaScript passaram. O teste de distribuição cobre 1 a 16 jogos e telas horizontais e verticais. O teste das skins verifica invalidação do cache, base monocromática com anotações coloridas, restauração da aparência normal e preservação da partida.

No navegador, em 1280 × 720: tabuleiro do operador com 450 pixels, destaque OBS com 510 pixels e quatro tabuleiros iguais de 302 pixels no mosaico OBS. Conferidos os três temas, ferramentas, letras automáticas sem alterar os lances, tradução dos tooltips, skins, preferência salva e sincronização com OBS. A lista de miniaturas foi conferida com 208 pixels de altura visível e 794 pixels de conteúdo: a rolagem moveu apenas essa lista. A troca de jogo pela miniatura manteve sua posição de rolagem. O destaque e o mosaico OBS permaneceram corretos após a mudança dos elementos na página.

Captura do ajuste mais recente: `validacao/miniaturas-sob-ferramentas-cores.png`. Outras capturas: `validacao/aurora-tabuleiro-maior-ferramentas.png`, `validacao/aurora-tabuleiro-preto-branco.png` e `validacao/obs-mosaico-uniforme.png`. Capturas de propostas anteriores foram preservadas apenas para referência.
