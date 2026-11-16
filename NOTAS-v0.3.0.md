# Aurora Pandanet Studio 0.3.0

Esta versão acrescenta consulta de jogadores e de partidas arquivadas, histórico de graduação por ano e localização inicial em 48 idiomas escritos. Continua sendo um aplicativo local, sem mudanças na arquitetura de hospedagem ou de múltiplos usuários.

## Atualizar e abrir

Encerre a versão anterior. Extraia o pacote e abra **Abrir Aurora.command**. Para manter seus dados, copie a pasta `data/` da instalação anterior para a nova antes de abri-la. O ZIP não contém banco pessoal, senhas, cookies nem sessões autenticadas.

## Jogadores e partidas

- **Buscar usuário Pandanet** pesquisa nomes e contas na base das ligas e contas no site. Sem autenticação, a base local continua funcionando e a tela informa como entrar para complementar a pesquisa.
- Clique no jogador para abrir **Informações** e **Partidas arquivadas**. A primeira aba mostra foto, bandeira, nome, país representado, graduação e ano. A ausência de foto usa uma silhueta; país desconhecido permanece vazio, sem bandeira presumida.
- A precedência é: edição local por ano para graduação e país; cadastro da liga correspondente ao ano; informações públicas do perfil para campos ausentes. Sem graduação de liga no ano, usa-se a registrada na própria partida. Nome e foto podem ter personalização local. Não se procura graduação em outro ano ou em outra liga.
- A graduação exibida na lista do arquivo é a que o Pandanet registrou naquela partida. Ao carregar o jogo, o painel aplica a graduação da liga do ano correspondente. O perfil indica a origem da graduação.
- As edições de graduação e país feitas no perfil pertencem à liga e ao ano apresentados. Nome e foto são personalizações gerais. Campos vazios permitem usar os dados importados. Personalizações antigas sem ano são preservadas no banco, mas não substituem automaticamente a graduação histórica de uma partida datada.
- O pacote inclui as quatro temporadas atuais anteriormente disponíveis e o elenco latino-americano de 2025: **837 pessoas distintas e 935 participações** em cinco temporadas. Outros anos são consultados no arquivo oficial de temporadas, sob demanda e em segundo plano. Uma indisponibilidade da fonte mantém o cadastro anterior e o uso da graduação da partida.
- Temporadas que abrangem dois anos cobrem ambos os anos indicados. Quando duas temporadas cobrem o mesmo ano, a temporada selecionada tem prioridade; na ausência dela, usa-se a mais recente cadastrada que cubra o ano. Uma gravação sem data não recebe uma graduação de liga presumida.

### Arquivo Pandanet

**Entrar no arquivo Pandanet** autentica no Net Social Plaza por HTTPS, independentemente da conexão ao servidor de partidas. Se houver uma conta registrada já conectada ao IGS, ela pode ser usada para autenticar a consulta quando necessário. É possível encerrar a sessão do arquivo pelo botão **Desconectar** na aba de partidas.

O histórico tem paginação. **Carregar partida** busca o SGF e abre a gravação no tabuleiro principal. Ela participa das miniaturas, do mosaico, da análise local e da saída OBS, e pode ser removida normalmente. Nenhum lance é enviado ao servidor. Uma nova conexão ou demonstração inicia outro contexto e limpa as partidas e análises anteriores, como nas versões anteriores.

São lidos o primeiro jogo e a primeira variante do SGF, incluindo passes e posições iniciais com pedras de handicap. Arquivos inválidos, coordenadas fora do tabuleiro e edições de posição no meio da partida são recusados com uma mensagem. Isso não é ainda um editor completo de árvores SGF.

**Validação real com HelcioAlex:** autenticação, perfil público de país, busca da própria conta, 50 registros na primeira página, 20 na segunda, download do SGF de 29/09/2026 e navegação dos oito lances na interface. A correção local para 2 dan em 2026 foi testada em banco temporário, sem alterar o cadastro pessoal da instalação existente.

**Divergência da fonte:** a página oficial da equipe brasileira consultada para 2026 ainda informa **3 dan** para HelcioAlex. O importador mantém o valor publicado; uma correção para **2 dan** pode ser salva no perfil de 2026, sem alterar 2025. Não foi introduzida uma exceção de código para um jogador específico.

O código identifica o link público **View all game results**, distinguindo-o de **View your game results**, que mostra somente os confrontos da conta conectada com o jogador. Após autorização explícita, o arquivo de **pooh88879** também foi validado: 58 páginas disponíveis, 50 registros em cada uma das duas primeiras páginas e carregamento da partida c10009 × pooh88879 de 17/10/2026. Os 75 lances foram reconstruídos e as 76 posições, incluindo o tabuleiro inicial, foram verificadas pelo estúdio. A sessão de teste foi encerrada. O relatório está em `validacao/arquivo-terceiro-v0.3.0.json`. A interface informa quando o site não fornece um arquivo público. Restrições de privacidade do site são respeitadas; campos privados visíveis ao próprio dono não são importados para a transmissão.

## Idiomas

O seletor no cabeçalho apresenta cada idioma pelo próprio nome. A escolha é salva no navegador e compartilhada com a saída de transmissão no mesmo perfil. Mudar de idioma preserva o tabuleiro, a posição de análise e as marcações.

São fornecidos catálogos locais com **103 mensagens por idioma**, reutilizadas nos controles, indicações de estado, diálogos e ajuda breve. O aplicativo não consulta tradutores durante o uso. Os textos foram traduzidos pelo modelo, com conferência dos termos asiáticos de Go na Sensei’s Library. As traduções são uma versão inicial e ainda não foram revisadas por falantes nativos, sobretudo nos idiomas de menor disponibilidade de material.

Português, English, Español, Français, Deutsch, Italiano, Nederlands, 日本語, 한국어, 简体中文, Svenska, Suomi, Dansk, Norsk bokmål, Norsk nynorsk, Polski, Čeština, Slovenčina, Slovenščina, Hrvatski, Српски, Български, Română, Magyar, Lietuvių, Ελληνικά, Türkçe, Gaeilge, Rumantsch, Kreyòl ayisyen, Русский, Українська, ქართული, Қазақша, Кыргызча, עברית, العربية, ⵜⴰⵎⴰⵣⵉⵖⵜ, Afrikaans, isiZulu, isiXhosa, isiNdebele, Sepedi, Sesotho, Setswana, siSwati, Tshivenḓa e Xitsonga.

Árabe e hebraico usam direção de leitura da direita para a esquerda. O tabuleiro e seus controles de navegação conservam a orientação. A fonte Tifinagh incluída garante os caracteres amazigues. Datas da interface usam o idioma escolhido; os horários de registros do Pandanet preservam o horário informado pela fonte, sem conversão de fuso presumida.

Nomes de jogadores, contas, equipes, títulos oficiais de competições e resultados/comentários originais do servidor são dados e permanecem na forma recebida. Mensagens técnicas não catalogadas podem conservar o texto original. O escopo escolhido nesta etapa é o dos idiomas escritos oficiais de alcance nacional; idiomas oficiais apenas em regiões e línguas de sinais não foram incluídos. Os casos interculturais específicos do Equador, **kichwa e shuar**, ainda estão pendentes; portanto a cobertura de todas as categorias de idioma oficial não deve ser considerada encerrada.

Os 48 catálogos foram alternados na interface de desktop: não houve perda da posição da análise nem rolagem horizontal na tela testada. Essa verificação não é uma certificação linguística nem substitui testes em todos os tamanhos de tela.

## Responsividade e dados

O acompanhamento IGS continua no seu worker. Consultas HTTPS, importações históricas e leitura de arquivos rodam fora dele. A navegação, as variantes, as marcações e o desenho continuam locais, sem esperar respostas de perfil ou arquivo. Não foi reintroduzida consulta periódica de estado; a consulta de conclusão de uma tarefa só existe enquanto aquela consulta está pendente.

Senhas, cookies, URLs autenticadas e identificadores remotos do arquivo ficam em memória. O navegador recebe identificadores temporários locais para carregar os registros, sem receber o token de sessão do site. Redirecionamentos do cliente de arquivo são limitados a HTTPS nos dois domínios oficiais do Net Social Plaza. Perfis consultados no site têm cache apenas em memória; só uma edição explicitamente salva grava esses campos no banco.

Validação automatizada: 48 testes Python e quatro conjuntos JavaScript. Abrange graduação por ano, correção isolada, bandeiras sem valores presumidos, leitura SGF, dados públicos, paginação, bloqueio de origens externas e análise local durante consulta remota lenta. As instâncias temporárias de teste são encerradas após a validação.

## Fontes e licenças

- [Pandanet — uso do Net Social Plaza e arquivo de jogos](https://pandanet-igs.com/communities/pandanet/11)
- [Brasil — elenco de 2026](https://pandanet-igs.com/communities/latinamericanleague/teams/48/BRA)
- [Arquivo de temporadas latino-americanas](https://pandanet-igs.com/communities/latinamericanleague/seasons)
- [Sensei’s Library — Liberty](https://senseis.xmp.net/?Liberty): 气, 呼吸点, 활로.
- [Sensei’s Library — Variation](https://senseis.xmp.net/?Variation): 变化, 変化.
- [Unicode CLDR — dados suplementares de idiomas e territórios](https://github.com/unicode-org/cldr/blob/main/common/supplemental/supplementalData.xml), usados como apoio ao levantamento, não como única classificação jurídica.
- [Assembleia Nacional do Equador — idiomas de relação intercultural](https://www.asambleanacional.gob.ec/es/noticia/portal-web-de-asamblea-se-publicara-en-kichwa-por-el-dia-de-la)
- Bandeiras: [flag-icons](https://github.com/lipis/flag-icons), licença MIT incluída em `static/flags/LICENSE.txt`.
- Fonte: [Noto Sans Tifinagh](https://github.com/google/fonts/tree/main/ofl/notosanstifinagh), SIL Open Font License incluída em `static/fonts/OFL.txt`.
