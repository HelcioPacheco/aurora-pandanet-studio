# Aurora Pandanet Studio — 0.4.7

Aplicativo local para acompanhar e comentar partidas do Pandanet. Inclui conexão ao servidor, seleção de salas e partidas, visualização em destaque ou mosaico, relógios, perfis locais e análise independente dos lances ao vivo.

**Novidades desta versão:** veja [NOTAS-v0.4.7.md](NOTAS-v0.4.7.md). Preserve a pasta `data/` ao atualizar. As seções de versões anteriores abaixo registram a evolução do aplicativo.

## Instalação a partir deste repositório

O pacote completo inclui a rede b18. Se você clonou o código pelo GitHub, baixe a [rede b18 oficial](https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b18c384nbt-s9996604416-d4316597426.bin.gz) e salve-a, sem descompactar, como `static/vendor/katago/b18-s9996604416.bin.gz` para ativar a análise. O SHA-256 esperado está em `engine-src/provenance.json`.

## KataGo no navegador — 0.4.6

Clique em **AI** para ligar a análise e mostrar a primeira sugestão na posição exibida. O botão alterna a sugestão sem jogar o lance. Na engrenagem, você pode ligar somente as avaliações, escolher intensidade, probabilidade de vitória ou vantagem em pontos e o que aparece no OBS.

A rede **b18** e o motor vêm no pacote. A análise roda localmente, em um trabalhador separado da interface. O navegador usa WebGPU quando disponível e CPU em caso contrário. Um único motor atende as partidas acompanhadas, prioriza a posição principal e conserva resultados por posição, histórico, regras, komi e pedras iniciais. Navegar, criar variantes e receber novos lances não bloqueiam a interface esperando a IA. Os percentuais de pretas e brancas e a vantagem em pontos ficam visíveis na partida principal, nas miniaturas e no OBS. A opção de probabilidade/pontos escolhe a escala da barra. Uma posição ainda não avaliada exibe uma barra neutra com traços, conservando a mesma altura.

A análise está limitada a **19 × 19** nesta versão. A primeira inicialização carrega cerca de **94 MiB** de rede. A memória inicial do motor é 512 MiB, além dos recursos da rede/GPU e do navegador. A velocidade depende do equipamento: CPU é consideravelmente mais lenta. Os níveis controlam limites de visitas e tempo, sem prometer uma profundidade fixa; o tooltip informa as visitas efetivamente realizadas.

As regras e o komi vêm dos dados da partida. Se o komi estiver ausente, os valores configurados são usados: inicialmente 6,5 ou 0,5 com handicap; o tooltip identifica esse uso como padrão. Sem regras informadas, o modo automático usa regras japonesas. É possível escolher outra regra. Resultados com posições divergentes, lances ilegais ou valores inválidos são descartados.

O OBS recebe os resultados da janela de operação pelo canal do navegador e não inicia outro motor. Continuam valendo as instruções de captura de janela abaixo. Mantenha a janela de operação aberta. O servidor fornece isolamento de origem para a memória compartilhada; as fotos externas são carregadas por uma rota local com cache para continuar disponíveis sob esse isolamento.

Validação desta versão: Chromium 155 com WebGPU e CPU, quatro posições comparadas entre os backends, navegação com IA ativa, barras nas quatro gravações e sincronização com a saída limpa. Safari ainda não foi validado nesta versão. Proveniência, licenças e instruções de recompilação: `engine-src/` e `static/vendor/katago/licenses/`.

## Abrir no Mac

Dê dois cliques em **Abrir Aurora.command**. O aplicativo abre no navegador em **http://127.0.0.1:8765**. Mantenha a janela do Terminal aberta; para encerrar, pressione Control+C nela. Requer Python 3.9 ou posterior; não requer instalação de bibliotecas.

Alternativa, a partir desta pasta:

```
python3 app.py --open
```

Se a porta já estiver em uso, abra o endereço acima para reutilizar o aplicativo. Para uma segunda instância, use `python3 app.py --port 8766 --open`.

## Usar

1. O estúdio inicia em **demonstração**, com quatro partidas reais gravadas. A indicação de gravação fica visível; elas não são apresentadas como partidas ao vivo.
2. Clique em **Conectar** para usar sua conta Pandanet ou entrar como visitante. Contas de visitante não podem entrar nas salas restritas, incluindo as da Liga e dos bots.
3. Escolha a sala. A liga é associada automaticamente; na sala europeia compartilhada, escolha a liga principal ou juvenil no subseletor. Selecione uma temporada e uma equipe para filtrar as partidas. **Acompanhar partidas da equipe** abre somente os jogos que ainda não estão sendo acompanhados ou abertos. **Todas as equipes** permite acompanhar apenas partidas individuais. Em salas sem liga, os controles de liga ficam desabilitados.
4. Clique nas miniaturas para trocar a partida principal. **Mosaico** mostra todas as partidas; clicar em uma delas retorna ao destaque.
5. Clique nos nós da árvore à direita do tabuleiro para navegar pelos lances e variantes. Os lances comuns são compartilhados, sem duplicação de linhas. Em telas estreitas, a árvore fica abaixo do tabuleiro. Você também pode usar os botões, a barra ou ←/→. Use ↑/↓ para alternar continuações irmãs e a lista de variantes para escolher outra linha. Home/End vão ao início/fim da linha; Page Up/Page Down e Shift+←/→ percorrem dez lances. Clicar em um lance existente apenas navega e preserva sua continuação. Clique no tabuleiro para criar uma variação. **Voltar ao vivo** retoma o acompanhamento da posição mais recente.
6. Use triângulo, círculo, quadrado, texto, seta ou lápis para comentar visualmente. Cada partida conserva sua posição de análise e suas marcações ao trocar o destaque. Os lances reais continuam chegando.
7. Clique no nome/foto de um jogador para cadastrar seu nome completo, país, graduação e endereço HTTPS de foto. Na ausência de foto, aparece uma silhueta. Os perfis são persistidos em `data/players.sqlite3`.

## Saída para OBS

**Saída OBS** abre uma segunda janela, sem controles de operação. Se o navegador bloquear a janela, abra **http://127.0.0.1:8765/?output=1** manualmente no mesmo navegador.

Capture essa janela no OBS. Ela acompanha a seleção de partida, o mosaico, a posição de análise e as marcações da janela de operação. A sincronização usa o armazenamento do navegador; ambas precisam usar o mesmo perfil e exatamente o mesmo endereço base (não misture `localhost` e `127.0.0.1`).

Para usar uma fonte Navegador interna do OBS, ainda será necessário implementar sincronização de seleção no servidor: o navegador embutido do OBS não compartilha o armazenamento do seu navegador. Nesta versão, use **captura da janela** da saída limpa.

## Dados e credenciais

O servidor atende somente neste computador. A senha não é escrita em arquivos: fica em memória enquanto a conexão está aberta, para permitir a reconexão. Ao desconectar ou fechar o aplicativo, as credenciais são descartadas. Não há envio de lances ou mensagens aos jogadores.

Posições de análise, variações e marcações ficam no armazenamento local do navegador. Iniciar uma nova conexão ou trocar para demonstração limpa o contexto anterior para evitar associar análises a números reutilizados pelo servidor.

## Verificação

```
python3 -m unittest discover -v
```

17 testes verificam reconstrução de posições, capturas, suicídio, ko simples, passes, handicap, isolamento de análise, API local, perfis e proteção de requisições. A comunicação usa a camada validada anteriormente em testes reais de reconexão e acompanhamento simultâneo.

A interface também foi testada no navegador com conexão real de visitante, duas partidas, relógios, variação local, alternância de destaque, mosaico e sincronização da janela limpa. Layouts de desktop e tela estreita foram inspecionados.

## Limites desta primeira versão

- O banco de perfis começa vazio. O cadastro é manual; a importação automática dos perfis da Liga por temporada é uma próxima etapa.
- Há uma sequência de variação local por partida, sem árvore completa de variações ou exportação SGF/PNG da análise.
- As ferramentas didáticas completas do Aurora SGF Studio, incluindo nuvens de liberdade e territórios, ainda não foram migradas.
- A regra de ko implementada para análise é o ko simples. Não há superko nem contagem automática de território.
- Uma partida com histórico inválido exibe erro em vez de inventar a posição. Relógios locais são estimativas entre atualizações do servidor.
- Ainda precisa de validação durante uma transmissão completa.

## Aparência — 0.1.1

As pedras têm desenho vetorial próprio, inspirado em ardósia fosca e concha com veios finos. A textura e sua orientação permanecem estáveis entre atualizações. Nenhuma imagem ou peça do q5Go é usada.

O seletor **Tema**, no cabeçalho, alterna entre **Claro** e **Escuro**. A escolha é lembrada no navegador e acompanha a janela limpa do OBS quando ambas usam o mesmo perfil e endereço base. O tema claro usa marfim, cinzas quentes e verdes suaves.

## Correções — 0.1.2

- **Remover partidas:** o botão fica sempre visível nas miniaturas e também abaixo do tabuleiro principal. A retirada da transmissão é local e imediata, mesmo com a partida encerrada, o servidor indisponível ou uma resposta demorada. Atualizações posteriores não recolocam o jogo removido.
- **Troca de sala:** a lista anterior é bloqueada e substituída por uma indicação de carregamento até a chegada das partidas da sala escolhida. Foram abertas, pela interface autenticada, duas partidas reais da Humanlike bots (99), com bots nas duas cores. A sala exige uma conta registrada.
- **Atualizações:** a interface recebe eventos por uma conexão HTTP persistente (SSE), em vez de consultar o estado a cada segundo. Os relógios avançam localmente e não recriam os tabuleiros. Cada miniatura só é redesenhada quando seus dados visuais mudam; a visualização oculta não é renderizada.
- **Comunicação:** a consulta periódica leve mantém a lista e verifica a conexão. Históricos completos são solicitados na abertura, reconexão, desfazer ou lacunas, sem baixar todos os jogos a cada 30 segundos.
- **Cache:** perfis são lidos do banco quando mudam; posições de análise continuam em cache quando chegam apenas novos lances posteriores.

Validação: 17 testes automatizados passaram, incluindo retirada de jogo encerrado com resposta remota bloqueada/recusada, mensagens SSE e estabilidade dos relógios. Na interface, foram testadas a abertura de dois jogos da sala 99, a retirada de ambos (incluindo o principal) e a preservação do tabuleiro durante os ticks do relógio. Isso confirma as causas corrigidas; ainda não substitui um teste de transmissão inteira na máquina de operação.

Para atualizar uma instalação anterior, encerre o aplicativo no Terminal e substitua os arquivos pela versão nova, preservando a pasta `data/` se houver perfis cadastrados. O pacote não inclui credenciais nem substitui esse banco local.

### v0.1.3 — Ferramentas do tabuleiro

Escolha a ferramenta pelo seletor. Letras seguem A, B, C… Z, AA…; números seguem 1, 2, 3… em uma sequência independente. Clique novamente na mesma marca com a ferramenta correspondente para removê-la, ou use Apagar marcação. As sequências são reorganizadas na ordem em que as marcas foram criadas. Limpar remove todas as marcações da posição atual.

Em Liberdades do grupo, clique em uma pedra: os pontos livres são circulados e a contagem aparece na pedra escolhida. Clique novamente no mesmo grupo para retirar essa indicação. As marcações continuam vinculadas à posição de análise e são compartilhadas com a saída de transmissão.

### v0.1.4 — Resposta local da interface

Navegação e variações são calculadas no navegador, sem solicitações HTTP. O motor mantém as posições anteriores em cache e invalida o trecho afetado quando um registro é corrigido. A renderização preserva as pedras existentes, adiciona/remove apenas as alteradas e atualiza marcações em uma camada separada. A seleção também preserva os tabuleiros das miniaturas. O servidor Python continua responsável pela conexão Pandanet, perfis e posição recebida.

Validação: 18 testes Python, incluindo equivalência de 589 posições/casos entre o motor do navegador e o motor Python. Testes JavaScript adicionais cobrem captura, suicídio, ko, ocupação, correções de histórico, novos lances, letras, números e liberdades.

Medição em demonstração local, do início do manipulador do comando até o próximo requestAnimationFrame: 10 navegações: 10,8 / 26,7 / 2,5 / 3,7 / 2,8 / 4,2 / 3,0 / 4,6 / 5,1 / 3,9 ms. Uma variação: 13,9 ms; uma letra: 3,7 ms. Essa medição indica o trabalho até o próximo quadro; não inclui o tempo de resposta remoto nem mede a apresentação física no monitor. O valor mais recente fica no atributo data-feedback-ms do tabuleiro para diagnóstico.

### v0.1.5 — Desenho, sincronização e salvamento separados

O tabuleiro principal e as miniaturas usam Canvas com texturas de pedras reaproveitadas. A navegação desenha somente a posição mais recente de cada quadro; sincronização da saída e gravação da disposição ficam fora do clique. A saída recebe cada atualização por um único canal. A abertura da aplicação também distingue versões para evitar reutilizar um servidor antigo silenciosamente.

A análise, comparação de desempenho e limites da medição estão em `ARQUITETURA.md`. O teste de diagnóstico fica disponível acrescentando `?diagnostics=1` ao endereço local; não é necessário ativá-lo para usar o programa.

### v0.2.0 — Ligas e cadastro de jogadores

Use **Liga** e **Temporada** na barra lateral. **Equipes e jogadores** abre a pesquisa por nome ou conta Pandanet, com filtro de equipe/país e cartões paginados. **Editar perfil local** personaliza os dados usados na transmissão. Ao acompanhar uma partida, a conta Pandanet associa automaticamente o jogador ao cadastro; a ausência de foto usa a silhueta.

A versão inclui os cadastros publicados da Liga Latino-Americana (2026), Liga Europeia (2026/2027), Liga Europeia Juvenil (2026) e AGA City League (2026): 101 equipes e 806 pessoas distintas, incluindo capitães. A equipe Toronto 2 consta sem elenco publicado na fonte. Estes números não significam que foram importados todos os jogadores históricos ou de todo o mundo; o escopo é o elenco publicado das quatro temporadas indicadas.

A base distingue pessoa, contas Pandanet, competição, temporada e participação em equipe. A mesma conta, sem distinguir maiúsculas, identifica a mesma pessoa; nomes iguais, sozinhos, não provocam fusão de cadastros. As graduações e o país/equipe representados são associados à temporada. O país representado não é tratado como prova de nacionalidade.

**Atualizar do Pandanet** consulta a temporada mais recente anunciada e lê seus elencos em segundo plano, sem bloquear o worker IGS ou a análise local. Uma falha de leitura preserva o cadastro anterior. Os dados já importados continuam disponíveis sem rede; as fotos dependem do endereço oficial ou personalizado. A atualização não apaga as personalizações salvas em `players`.

As temporadas importadas são preservadas e aparecem no seletor. Esta versão inicia com uma temporada por liga; não importa automaticamente o arquivo histórico inteiro. O link oficial “Teams/current” pode estar desatualizado, por isso a temporada é identificada pelo painel atual da página principal e registrada com fonte e data.

Ao conectar ao IGS, **Ir à sala da liga** aparece quando a sala correspondente é encontrada na lista recebida. A sala juvenil não foi presumida: ela pode ser escolhida manualmente. Escolher liga não remove partidas nem apaga análises.

O banco permanece em `data/players.sqlite3`. Na primeira migração de um cadastro com perfis locais, uma cópia `data/players.before-leagues.sqlite3` é criada antes de acrescentar as tabelas. Preserve toda a pasta `data` ao atualizar. A distribuição ZIP contém apenas os cadastros públicos iniciais em `league-seed`, sem o banco pessoal.

Fontes oficiais:
- https://pandanet-igs.com/communities/latinamericanleague/teams/48
- https://pandanet-igs.com/communities/euroteamchamps/teams/49
- https://pandanet-igs.com/communities/PYGETC/teams/47
- https://pandanet-igs.com/communities/agacityleague/teams/46

Validação desta versão: 34 testes Python e três conjuntos de testes JavaScript. Inclui correspondência de contas, graduação por temporada, preservação de edições locais, cópia de segurança, importação atômica e análise local durante uma atualização de fonte indisponível.

### v0.2.1 — Variações automáticas e numeração dos lances

O botão Criar uma variação foi removido. Com a ferramenta **Jogar / explorar lances**, clique no próximo lance registrado para avançar na partida; um lance legal diferente cria automaticamente uma variação local. Nenhum lance é enviado ao Pandanet. Um lance ilegal não altera a posição nem interrompe o acompanhamento ao vivo.

As setas percorrem a variação atual sem apagá-la. O contador e o controle de posição acompanham a sequência alternativa. **Voltar à partida nesta posição** retorna ao ponto de origem; **Voltar ao vivo** acompanha novamente o jogo recebido. Ao jogar outra continuação a partir do meio de uma variação, a sequência atual é substituída a partir desse ponto; esta versão não oferece ainda uma árvore com múltiplos ramos salvos.

**Numeração dos lances**, seguindo as opções do Aurora SGF Studio v0.4.6: Sem números; Último lance; Últimos 5, 10, 25 ou 50; Todos os lances. O padrão é Último lance. A preferência é preservada e compartilhada com a saída OBS. Nas variantes a numeração recomeça em 1, inclusive quando se cria uma alternativa no meio de uma continuação. Os passes contam na sequência, mas não recebem rótulo em uma interseção. O posicionamento de handicap não é numerado como lance. Pedras capturadas não exibem números. Letras, números manuais e a contagem de liberdades têm prioridade sobre a numeração automática no mesmo ponto.

O cálculo e o desenho continuam locais, com Canvas e a fila por quadro. A versão passou nos 34 testes Python existentes e nos quatro conjuntos JavaScript, incluindo o novo teste das variações e dos sete modos de numeração. A criação automática, navegação e sincronização da numeração com a saída foram conferidas na interface.
