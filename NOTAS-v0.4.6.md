# Aurora Pandanet Studio 0.4.6

Primeira integração do KataGo b18 no navegador.

- Barras de avaliação na partida principal, miniaturas e mosaico; preto corresponde às chances/vantagem das pretas. Passe o ponteiro para consultar os valores e as visitas.
- Botão AI mostra a primeira sugestão como círculo azul numerado e coordenada, incluindo posições históricas e variantes. Não joga nem altera a árvore.
- Configuração de intensidade, probabilidade/pontos, regras, komi quando ausente e visibilidade independente de avaliações/sugestões no OBS.
- Um motor em trabalhador separado, fila com prioridade para a posição exibida, cache e rejeição de resultados antigos após mudanças de posição. OBS compartilha os resultados.
- Rede b18 incluída; WebGPU com alternativa em CPU. Sem serviço externo de análise.
- Rótulos dos novos controles nos 48 idiomas existentes.
- Metadados KM/RU preservados ao importar SGF. Isolamento necessário ao motor e cache local de fotos públicas HTTPS.

Limites: tabuleiros 19×19; uso relevante de memória e desempenho dependente do equipamento. Validado em Chromium 155, incluindo os backends WebGPU e CPU; Safari pendente. As avaliações são estimativas da rede e os níveis de análise são limitados por visitas/tempo. Consulte o README para komi/regras e uso no OBS.

## Ajuste da apresentação das avaliações

A barra sem avaliação usa uma classe própria, evitando o espaçamento da tela vazia. Os estados pendente, desativado e avaliado conservam a mesma altura. Valores ausentes ou inválidos aparecem como traços.

Percentuais de pretas/brancas e vantagem em pontos ficam permanentemente visíveis na partida principal, miniaturas e OBS. A opção de probabilidade/pontos continua escolhendo a escala da barra. A apresentação usa como referência a transmissão da BadukTV em https://www.youtube.com/watch?v=qEIWvWTTZ5I&t=3600s, mantendo a identidade do Aurora.

Verificado no navegador com avaliações reais, estado sem análise, mosaico OBS de quatro tabuleiros iguais de 302px e 13 conjuntos de testes JavaScript. Aplicado à instância em execução; o ZIP original da 0.4.6 permanece inalterado.
