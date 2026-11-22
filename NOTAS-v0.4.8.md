# Aurora Pandanet Studio v0.4.8

Primeira release pública do estúdio de transmissão e análise de partidas do Pandanet.

## Novidade desta versão

A opção **Último lance** vem ativada por padrão no mosaico, nas miniaturas e na saída OBS. Marca a pedra mais recente, permite desativação, salva a preferência e não mantém uma marca antiga após passe. O controle fica ao lado de Destaque/Mosaico.

## Recursos incluídos

- Acompanhamento de partidas do Pandanet, seleção de salas e filtros por equipe nas salas das ligas.
- Visualização em destaque ou mosaico e janela limpa para captura no OBS.
- Navegação por lances e variantes, grafo, atalhos de teclado e ferramentas de anotação.
- Perfis de jogadores, bandeiras e integração com cadastros das ligas.
- Temas escuro, claro e azul claro; tabuleiro normal ou preto e branco.
- KataGo b18 no navegador, avaliações numéricas visíveis e primeira sugestão da IA.
- Interface com 48 idiomas.

## Instalação

Baixe **Aurora-Pandanet-Studio-v0.4.8.zip**, extraia a pasta e abra **Abrir Aurora.command** no Mac. Requer Python 3.9 ou posterior. A alternativa é executar `python3 app.py --open` na pasta extraída. O pacote completo inclui a rede b18; os arquivos de código-fonte gerados pelo GitHub exigem o download separado da rede, conforme o README.

Preserve a pasta `data/` se estiver atualizando uma instalação anterior. Dados locais e credenciais não estão no pacote.

## Validação e limites

84 testes Python e 14 conjuntos JavaScript. A nova marcação foi conferida no navegador e no OBS, incluindo persistência da opção. A análise de IA suporta 19×19 e depende do desempenho do equipamento; Safari ainda não validado. Para OBS, use captura da janela limpa no mesmo navegador/perfil da operação.
