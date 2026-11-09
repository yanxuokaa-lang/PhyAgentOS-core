# Tetris × Jev

Uma demo em que o **Jev, da TypeSafe AI, joga Tetris**: o modelo escolhe a rotação e a posição de cada peça, e o jogo transforma a decisão estruturada em movimentos reais.

Interface arcade em Canvas 2D, com a decisão em JSON, confiança, latência e custo estimado da partida visíveis durante o jogo. JavaScript e Node.js, sem dependências externas.

## Rodar localmente

Requer **Node.js 22 ou superior**. Para jogar com IA, configure uma chave da [TypeSafe](https://console.typesafe.ai) com créditos disponíveis.

```sh
git clone https://github.com/marcelomar21/demo-tetris-jev.git
cd demo-tetris-jev
cp .env.example .env
```

Edite `.env` e preencha `TYPESAFE_API_KEY`. Depois:

```sh
node --env-file=.env server.cjs
```

Abra **http://127.0.0.1:8765** e clique em **Iniciar jogo**. Não há `npm install` nem etapa de build.

Para jogar sem IA, selecione **Marcelinho joga**. Esse modo também funciona abrindo `index.html` diretamente, sem servidor ou credencial.

### Configuração

| Variável | Uso |
| --- | --- |
| `TYPESAFE_API_KEY` | Chave da API, usada exclusivamente pelo servidor. |
| `PORT` | Porta local; padrão `8765`. |

O servidor também aceita a chave em `~/.typesafe-api-key` como alternativa, caso a variável esteja vazia. O arquivo `.env` é carregado pelo argumento `--env-file`, não automaticamente pelo código.

### Controles

| Tecla | Ação no modo manual |
| --- | --- |
| `←` / `→` | Mover |
| `↑` | Girar |
| `↓` | Descer |
| `Espaço` | Soltar |
| `P` / `Esc` | Pausar ou continuar |

Há controles na tela para dispositivos de toque. O jogo pausa ao perder o foco ou ficar em uma aba oculta.

## Como o Jev joga

1. O motor enumera os encaixes alcançáveis e calcula suas métricas: linhas completas, buracos e altura resultante.
2. O servidor envia o tabuleiro e essas alternativas ao [endpoint System One da TypeSafe](https://docs.typesafe.ai/introduction), usando `jev-latest` e uma pergunta `choice`.
3. O Jev escolhe uma alternativa que combina rotação e posição. O servidor valida a resposta; o navegador confere o caminho e executa os movimentos.
4. Enquanto a peça atual se move, uma consulta antecipada prepara a próxima. A previsão considera o encaixe e a remoção de linhas, usando apenas a fila de peças já conhecida.

A gravidade continua durante a consulta. A antecipação só é aproveitada quando o tabuleiro previsto se confirma e o caminho ainda é alcançável. Respostas antigas são descartadas. Há no máximo uma consulta em andamento e uma peça de antecedência.

O motor não escolhe uma jogada por heurística quando a API falha: a escolha é do Jev. A confiança exibida é a informada pelo modelo e não garante uma boa jogada.

### Velocidade

São **20 níveis**, com incrementos iguais de velocidade. No nível 20, a queda automática é de **2 células por segundo**; movimentos acontecem a cada 20 ms e a descida comandada a cada 45 ms. Isso dá margem à resposta enquanto mantém os encaixes rápidos.

Esse teto é conservador, não uma garantia de partida infinita: latência variável, pilhas altas e decisões ruins ainda podem causar game over.

### Custo da partida

O painel acumula uma **estimativa em USD** a partir dos tokens informados pela API. A tarifa de referência configurada no código, conferida em 18/09/2026, é **US$ 0,042 por milhão de tokens de entrada**, com saída gratuita ([fonte oficial](https://typesafe.ai/blog/introducing-system-one-models-and-jev)). Consulte o provedor para a cobrança vigente.

- Iniciar ou reiniciar zera o total da partida; pausar e trocar de modo preservam o total.
- Consultas antecipadas e decisões descartadas também contam quando o consumo é informado.
- Ao descartar uma jogada, o servidor deixa a consulta já enviada terminar para registrar o custo, mantendo o timeout de 12 segundos.
- Um `+` indica uma estimativa parcial: houve chamadas sem consumo informado. Não se assume custo zero nesses casos.

O registro fica apenas na memória do servidor, expira e não substitui a fatura da TypeSafe.

## Credenciais e execução local

A chave fica no servidor e é enviada somente para `api.typesafe.ai`. O navegador recebe o resultado da decisão e o consumo, sem a chave.

O `.gitignore` exclui `.env`, arquivos de chave e artefatos locais. O `.env.example` contém apenas campos vazios ou valores públicos. Nunca coloque a chave em `app.js`, no HTML, em capturas de tela ou em commits.

O servidor escuta apenas em `127.0.0.1`, valida origem e estado do jogo e serve uma lista explícita de arquivos públicos. `.env`, código do servidor e arquivos de chave não são servidos. Esta é uma demo local: publicar o código no GitHub não hospeda a integração da API.

## Testes

```sh
node --test engine.test.cjs moves.test.cjs server.test.cjs continuous.test.cjs
```

Os testes usam respostas simuladas e não consomem créditos. Cobrem regras, encaixes, validação da API, custo, cancelamentos, antecipação, queda contínua e velocidade.

## Estrutura

| Arquivo | Responsabilidade |
| --- | --- |
| `engine.js` | Regras, colisões, rotação, queda e pontuação. |
| `moves.js` | Alternativas alcançáveis e métricas de encaixe. |
| `server.cjs` | Servidor local, integração Jev e registro de custo. |
| `app.js` | Animação, decisões, antecipação e controles. |
| `index.html`, `style.css` | Interface arcade. |
| `*.test.cjs` | Testes automatizados. |
| `assets/` | Logo TypeSafe e referência da origem. |

A origem da marca usada no cabeçalho está documentada em [assets/SOURCES.md](assets/SOURCES.md).
