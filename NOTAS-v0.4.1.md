# Aurora Pandanet Studio 0.4.1

20 de outubro de 2026. Preserve sua pasta `data/` ao atualizar.

## Retorno a uma sala sem liga — 20/10/2026

- Sala, associação de liga e lista de partidas passam a ser publicadas juntas. Atualizações de perfis não expõem mais o nome da sala anterior enquanto os jogos já pertencem à nova sala.
- Durante a entrada, o seletor mantém a sala solicitada. A confirmação da sala é publicada antes da consulta de partidas; uma consulta lenta ou malsucedida não devolve o seletor à sala anterior.
- Em salas sem liga, os controles de temporada, equipes e carregamento por time são ocultados e desabilitados. Filtros da liga anterior são descartados; a busca de usuários e a observação individual continuam acessíveis.
- Uma importação de cadastro concluída após a saída da sala não reativa a liga anterior nem substitui uma temporada escolhida posteriormente.
- Corrigida a indicação antiga de versão no rodapé.

Validação: 73 testes Python e seis suítes JavaScript passaram. A simulação local do navegador conferiu a saída da liga com filtro de time ativo, o seletor da sala comum e a lista correspondente. Não houve autenticação no Pandanet nessa validação.

O pacote inclui estas correções, o código e os testes. Não inclui o banco local nem credenciais.
