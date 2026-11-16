# Aurora Pandanet Studio 0.4.0

20 de outubro de 2026. Preserve sua pasta `data/` ao atualizar; o pacote não inclui o banco local nem credenciais.

## Encerramento de partidas (20/10/2026)

- Preserva o registro encerrado diante de mensagens atrasadas, repetidas ou de outra partida que reutilize seu número.
- Confere a identidade dos jogadores antes de alterar um registro acompanhado.
- Não interpreta a repetição de um lance antigo como desfazer os lances seguintes.
- Recebe históricos completos separadamente e só os aplica ao terminar a resposta. Uma falha nessa consulta não desfaz um resultado recebido durante a sincronização.
- Mantém o último tabuleiro válido e sua lista correspondente de lances quando chega uma atualização ilegal; solicita sincronização enquanto a partida estiver ativa. Se o primeiro histórico já estiver inválido, exibe somente seu trecho inicial válido.
- Conserva resultado, jogadores, graduação e tamanho do tabuleiro quando o servidor reutiliza um número. Remover e acompanhar novamente inicia outro registro.

Validação: 61 testes Python da aplicação, 15 testes do protocolo com o transporte atualizado e quatro suítes JavaScript passaram. Na interface, uma simulação local confirmou a posição preservada após lance ilegal, encerramento e reutilização do número, além da navegação pelos lances sem erros no console.

Não houve reprodução de uma partida real específica: o relato não identificou um exemplo. As sequências de protocolo foram reproduzidas em testes controlados. As correções estão incluídas nesta versão.

## Equipes e salas (20/10/2026)

- A sala determina a liga. EuroTeamChamps e EuropeanTeamChamp são nomes associados à sala compartilhada pelas ligas europeias principal e juvenil; nela aparece um subseletor restrito às duas ligas. As demais associações são automáticas.
- Salas sem associação desabilitam temporada, cadastro de equipes e filtro de time. Busca de usuários e observação individual continuam disponíveis.
- O filtro usa as contas do elenco da temporada escolhida, em qualquer cor e sem diferenciar maiúsculas de minúsculas. Contas alternativas do cadastro também são consideradas. Mudar liga ou temporada limpa o filtro.
- O botão de acompanhar a equipe abre todas as suas partidas na sala, inclusive as que a busca textual não exibe, excluindo as já acompanhadas ou em processo de abertura. Sem elenco ou sem jogos novos, fica desabilitado.
- “Todas as equipes” mostra todas as partidas da sala e permite abertura individual, mas nunca carregamento em conjunto. O servidor também valida a equipe e a liga/temporada/sala do pedido e impede duplicatas.
- O novo botão tem tradução nos 48 idiomas existentes.

Validação final: 70 testes Python e cinco suítes JavaScript passaram. Na simulação local do navegador foram conferidos o filtro, abertura sem duplicação, bloqueio da opção geral, troca de salas, subseletor europeu e desativação dos controles em sala sem liga. Não houve conexão ao Pandanet nessa validação. O pacote inclui o código e os testes; não inclui dados locais de usuários.
