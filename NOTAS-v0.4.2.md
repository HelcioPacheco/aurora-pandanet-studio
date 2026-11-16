# Aurora Pandanet Studio 0.4.2

20 de outubro de 2026. Preserve sua pasta `data/` ao atualizar.

## Navegação de lances e variantes

- Na partida em destaque, ←/→ recuam e avançam um lance. Shift+←/→ e Page Up/Page Down percorrem dez lances. Home/End vão ao início/fim da linha selecionada.
- ↑/↓ e os botões correspondentes alternam continuações irmãs na bifurcação. Uma lista permite selecionar qualquer variante guardada ou a partida original.
- Clicar em um lance já existente, na linha original ou em outra variante, apenas navega para esse lance e mantém a continuação. Uma nova linha só é criada para uma continuação diferente e legal.
- As variantes são preservadas ao recuar antes da bifurcação, voltar à partida, acompanhar ao vivo, trocar de jogo e recarregar a página no mesmo navegador. Cada partida guarda suas próprias linhas e marcações.
- Os atalhos não interferem com campos de texto, seletores, diálogos, composição de texto ou atalhos do navegador. Não se aplicam ao mosaico nem à janela de saída OBS.
- Os novos controles usam as traduções existentes; a opção “Partida original” foi traduzida nos 48 idiomas disponíveis.

Validação: 73 testes Python e sete suítes JavaScript passaram. A simulação local no navegador conferiu variantes irmãs, navegação pelo teclado, preservação após recarregar, clique sem duplicação, campos de texto e isolamento entre partidas. Não houve autenticação no Pandanet nesta validação. O servidor de teste foi encerrado ao terminar.

O pacote inclui estas alterações, o código e os testes. Não inclui o banco local nem credenciais.
