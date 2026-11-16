# Aurora Pandanet Studio 0.4.4

24 de outubro de 2026. Preserve a pasta `data/` ao atualizar.

## Interface compacta

- Mantido o logo original de pedra e horizonte.
- Verdana menor nos controles e nomes; cabeçalho e espaçamentos reduzidos; títulos grandes e ornamentos retirados.
- Explicações e atalhos disponíveis no botão `?`, sem ocupar permanentemente a mesa.
- Temas claro e escuro neutros; menos molduras e repetição de indicadores.
- Miniaturas logo abaixo do quadro principal, independentemente da altura das ferramentas. Tamanho do tabuleiro preservado.
- A mensagem permanente de demonstração foi retirada da mesa, mantendo o estado no cabeçalho. Outros avisos continuam visíveis.

## Retorno à sala principal

O Pandanet confirma a saída com `9 You are leaving game room #…`. O reconhecimento anterior esperava `left`, causando timeout e mantendo a sala anterior no seletor mesmo quando a lista de partidas já era da sala principal.

A confirmação agora corresponde à resposta real e ao número da sala. Mensagens sobre outros jogadores não confirmam a troca. Entrar novamente na sala principal já selecionada preserva o estado e dispensa uma confirmação que o servidor não envia nesse caso.

Os recursos de liga são atualizados junto com a sala. A sala principal oculta temporada, times e consulta ao cadastro da liga, inclusive diante de metadados antigos. O grafo também deixa de apresentar elementos decorativos como imagens sem nome aos leitores de tela.

## Validação

80 testes Python e nove suítes JavaScript. A correção de sala foi conferida com conexão real ao Pandanet, alternando entre sala de liga e sala principal. O visual compacto foi conferido com partidas gravadas nos dois temas, ajuda, mosaico, navegação por botões e teclado e retorno ao vivo. Na janela de 1280 × 720, o tabuleiro mantém 300 pixels e as quatro miniaturas ficam visíveis, sem transbordamento horizontal.

A distribuição inclui o código, os testes e as capturas de validação. Não inclui banco pessoal nem credenciais.
