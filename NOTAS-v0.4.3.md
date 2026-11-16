# Aurora Pandanet Studio 0.4.3

23 de outubro de 2026. Encerre a versão anterior e preserve sua pasta `data/` ao atualizar.

## Sala principal e árvore de lances — 23/10/2026

- Respostas antigas não podem mais substituir estados mais recentes da mesma execução do servidor. Isso inclui respostas HTTP atrasadas e notificações recebidas fora de ordem, mesmo quando a sessão de conexão muda. Uma nova execução do aplicativo pode reiniciar a contagem de atualizações normalmente.
- O seletor trata o número 0 como sala principal e não cria uma segunda opção para ela a partir da lista do servidor. A sala principal não recebe associação de liga.
- Uma árvore vertical de lances e variantes ocupa o espaço livre à direita do tabuleiro. Em telas de até 900 px, aparece abaixo dele. A saída OBS mantém apenas o tabuleiro.
- Os nós numerados têm pedras de 18 px de diâmetro e uma área de clique maior. A posição atual e seu caminho ficam destacados; o grafo acompanha a navegação e permite rolagem independente.
- Clicar em um nó existente navega até ele sem criar variantes. Os caminhos comuns são compartilhados no grafo. Os atalhos de teclado continuam disponíveis.
- O título da árvore está traduzido nos 48 idiomas disponíveis.

Validação: 74 testes Python e nove suítes JavaScript passaram. Os testes exercitaram a função real que recebe os estados, com respostas antigas após a entrada na sala 0. A simulação local no navegador confirmou o seletor após carregar e atualizar jogos, cliques em variantes irmãs, nós menores e rolagem acompanhando a posição. Um teste da árvore cobre 3.000 lances sem recursão. Não houve conexão ao Pandanet nesta validação; o caso exato do usuário não foi gravado.

O pacote inclui estas alterações, o código e os testes. Não inclui o banco local nem credenciais.
