[English](troubleshooting.md) | **Português**

# 🩺 Solução de problemas

Procure o que está acontecendo com você, veja a causa provável e siga o que fazer. Enquanto roda, o app imprime linhas curtas de situação, em inglês (na janela da linha de comando, quando você inicia por ela). Muitos itens abaixo começam com o texto exato de uma dessas linhas, para você reconhecer. O que ainda não tem conserto não está nestas tabelas: está em [Limitações conhecidas](#-limitações-conhecidas). Voltar ao [README](../README.pt-BR.md).

## 🎮 Controles e mira

| O que acontece | Causa provável | O que fazer |
|---|---|---|
| O jogo joga sozinho depois que você solta os controles | O rastreamento de mãos (o headset seguindo as suas mãos sem controle, pelas câmeras) está ligado. Quando você solta os controles, o headset passa a seguir as mãos, a mira pula e um gesto de pinça com os dedos conta como gatilho | Desligue o rastreamento de mãos nas configurações do headset |
| O app não recebe os botões, ou o jogo enxerga dois controles | A opção **Use controllers as gamepad** está ligada na aba **INPUT** do Virtual Desktop. Assim, o Virtual Desktop toma os controles para ele | Desligue essa opção |
| Os controles param enquanto o menu do headset está aberto | É de propósito: com o menu do headset aberto, o app solta todos os botões e para a mira, para nada ficar apertado no jogo | Feche o menu do headset, e os controles voltam |
| O Y parece não apertar o TRIANGLE | O Y é a tecla de combinação. Apertado sozinho, ele envia TRIANGLE só quando você solta um aperto rápido, ou depois de 0,25 segundo quando você segura. Durante esse 0,25 segundo, o app espera para ver se você está começando uma combinação | Toque no Y e solte, ou segure um instante. Para mudar isso, veja `combo.solo_delay_s`, `combo.key` e `combo.solo` na [configuração](configuration.pt-BR.md) |
| Mexer o controle não move a mira no jogo | O jogo só usa o sensor de movimento quando a mira por giroscópio (por movimento) está ligada nele, e só se ele reconhecer o controle como um DualShock 4 | Nos ajustes de controle do jogo, ligue a mira por giroscópio. Depois ajuste a sensibilidade ali, antes de mexer no `gyro.scale` |
| A mira treme ou escorrega com a mão parada | Pequenos tremores da mão e do rastreamento do headset passam da zona morta (a faixa de movimentos pequenos que o app ignora) | Aumente um pouco o `gyro.deadzone_dps`, por exemplo para `3.0`, na [configuração](configuration.pt-BR.md) |
| A mira lenta e precisa parece travada | Movimentos mais lentos que a zona morta são ignorados | Diminua o `gyro.deadzone_dps`, por exemplo para `1.0` |
| A mira fica rápida ou lenta demais mesmo no limite do ajuste do jogo | A faixa de sensibilidade do jogo não basta para você | Mude o `gyro.scale` (acima de 1 fica mais rápida, abaixo de 1 fica mais lenta) |

## 🖥️ Tela e imagem

| O que acontece | Causa provável | O que fazer |
|---|---|---|
| A tela está de lado ou alta demais | A tela fica onde você recentralizou por último, e você se mexeu ou virou desde então | Segure os dois cliques dos analógicos (aperte os dois analógicos para baixo) por 1 segundo, olhando para onde você quer a tela. Veja também [Recentralizar a tela](usage.pt-BR.md) |
| A tela está perto ou longe demais | A distância que você ajustou dentro do headset ficou salva, e ela vale mais que o `screen.distance_m` | Segure o Y e mexa o analógico direito para a direita (aproxima) ou para a esquerda (afasta). Você também pode digitar a distância na página **Tela** da janela antes de apertar **Iniciar**. Pela linha de comando, inicie o app com `--distance` ou apague o `screen.json` em `%APPDATA%\vr-gyro-screen` |
| Detalhes finos, como letra pequena ou grama, cintilam | Os mipmaps vêm desligados. São cópias menores da imagem que mantêm os detalhes finos estáveis quando a imagem é reduzida para caber no headset, mas podem fazer o jogo engasgar | Coloque `capture.mipmaps = true` no arquivo de configurações (veja a [configuração](configuration.pt-BR.md)) e desligue de novo se o jogo começar a engasgar. Se já estiver ligado, veja "Detalhes finos cintilam mesmo com mipmaps ligados" em [Limitações conhecidas](#-limitações-conhecidas) |
| O fundo está preto em vez de mostrar o seu quarto | O `screen.background` está como `black` | Mude para `auto` ou `passthrough`. Se aparecer a linha `background: this runtime does not offer passthrough to apps; using black`, veja [Limitações conhecidas](#-limitações-conhecidas) |

## 🔌 Monitor e captura

| O que acontece | Causa provável | O que fazer |
|---|---|---|
| `no monitor matches "..."` | O texto em `screen.monitor` (ou em `--monitor`) não faz parte do nome de nenhum monitor. A linha também lista os monitores encontrados | Rode `vr-gyro-screen monitors` e use o número do monitor ou parte do nome dele |
| `there is no monitor N; M found` | O número é maior que o do último monitor da lista. A lista começa no 0 | Rode `vr-gyro-screen monitors` e use um número dessa lista |
| `Windows reports no monitor attached to the desktop` | O Windows não tem nenhum monitor ativo naquele momento | Confira se há um monitor ligado e conectado e inicie o app de novo |
| O monitor errado aparece no headset | Com `auto`, o app procura o monitor virtual do Virtual Desktop. Quando ele não existe, o app usa outro monitor que não seja o principal e, por fim, o principal | Confira no Virtual Desktop se o monitor virtual dele está ligado e rode `vr-gyro-screen monitors` para ver qual o app escolhe. Você também pode escolher pelo `screen.monitor` |
| `capture: lost the monitor (...); waiting for it to come back` | O Virtual Desktop remove o monitor virtual e cria outro quando você muda a taxa de quadros ou reconecta o headset | Espere alguns segundos. Quando o monitor novo aparece, surge a linha `capture: the monitor is back` e a imagem volta. O seu jogo pode precisar de um instante no monitor novo |
| `capture: could not reopen the monitor (...); still trying` | O monitor voltou, mas o app ainda não conseguiu montar a imagem de novo | Espere: o app tenta de novo a cada segundo, e os controles continuam funcionando enquanto isso. Se a imagem não voltar nunca, feche o app e inicie de novo |
| `could not capture the monitor: ...` | A captura não conseguiu começar quando o app abriu | Rode `vr-gyro-screen monitors` para conferir o monitor e depois tente iniciar com `--backend direct` |
| `the dxcam backend needs the optional package` | O `capture.backend` (ou o `--backend`) pede o `dxcam`, e esse pacote extra não está instalado | Volte o backend para `auto`, ou instale o pacote com `pip install ".[dxcam]"` na pasta do projeto |
| `rotated monitors are not supported` | O monitor está em retrato ou de cabeça para baixo nas configurações de tela do Windows | Ponha em paisagem no Windows, ou escolha outro monitor |
| O jogo não entra em tela cheia no monitor do headset | O jogo não recebeu a tecla de tela cheia logo depois que a janela dele foi movida | Rode `vr-gyro-screen window "parte do título"` de novo. Se o jogo não usa F11 para tela cheia, acrescente `--fullscreen-key alt+enter`, ou `--fullscreen-key none` para só mover e maximizar a janela |
| `Windows did not let the window come to the front, so no key was pressed; click it once` | O Windows só manda teclas para a janela que está na frente, e ele não deixou a janela do jogo vir para a frente | Clique uma vez na janela do jogo e rode o comando `window` de novo |
| `no visible window has "..." in its title` | Nenhuma janela aberta tem esse texto no título dentro do tempo de espera (60 segundos, por padrão) | Confira o título da janela do jogo e use uma parte dele. Se o jogo demora a abrir, use `--wait` com mais segundos |

## ⚙️ Instalação e configuração

| O que acontece | Causa provável | O que fazer |
|---|---|---|
| `vr-gyro-screen only runs on Windows` | O app foi iniciado em outro sistema | Rode no Windows |
| `configuration problem: ... has unknown keys` | Um erro de digitação num nome, ou uma opção que não existe | Compare o seu arquivo com o [config.example.toml](../config.example.toml). A mensagem diz o grupo e os nomes errados |
| `configuration problem: ... must be between ...` ou `... must be one of ...` | Um valor está fora da faixa aceita ou não é uma das palavras aceitas | Use um valor da página de [configuração](configuration.pt-BR.md) |
| `configuration problem: ... is not a gamepad button` ou `... is not a controller input` | Um nome de botão fora das listas | Use os nomes listados em [Mapeamento dos botões](configuration.pt-BR.md) |
| `configuration problem: combo.key ... is also used in [buttons]` (ou `[combo.with]`) | A tecla de combinação não pode ser também um botão comum, senão ela chegaria ao jogo em toda combinação | Tire esse botão de `[buttons]` ou de `[combo.with]` |
| `configuration problem: ... is not valid TOML` | O arquivo tem um erro de escrita, como uma palavra sem aspas ou um colchete faltando | Confira a linha indicada na mensagem. Texto vai entre aspas (`hand = "left"`); números e `true`/`false`, não |
| `configuration problem: configuration file not found` | O arquivo passado com `--config` não existe nesse caminho | Corrija o caminho. Sem `--config`, não ter arquivo na pasta padrão não é problema |
| `could not create the virtual gamepad (...)` | O driver ViGEmBus (o driver do Windows que cria o controle virtual) está faltando ou não funciona | Instale ou repare o ViGEmBus e inicie o app de novo |
| `the headset session failed (...)` | O headset não está conectado, ou o runtime OpenXR não está ativo. OpenXR é o padrão que permite ao app conversar com o headset; o runtime é o software no PC que faz esse trabalho, aqui o que vem com o Virtual Desktop | Conecte o headset pelo Virtual Desktop, confira se o runtime OpenXR do Virtual Desktop (VDXR) é o ativo e inicie o app de novo |

## 🐢 Desempenho

A cada 10 segundos, o app imprime uma linha de resumo (a não ser que você inicie com `--quiet`):

```text
90 frames/s, worst gap 12 ms, 0 late, capture 0.20 ms per frame, session FOCUSED
```

Os números acima só mostram o formato da linha; os seus vão ser outros.

| Parte da linha | O que significa | O que é bom |
|---|---|---|
| frames/s | Quantas imagens por segundo o app entregou ao headset | Perto da taxa de quadros do headset (por exemplo, 90) |
| worst gap | O maior intervalo entre duas imagens nesses 10 segundos. Um valor alto é um engasgo que você pode ter sentido | Perto de um quadro (cerca de 11 ms a 90 Hz) |
| late | Quantas imagens levaram um quadro e meio ou mais. Cada uma é um pequeno engasgo | 0, ou perto disso |
| capture | Tempo médio gasto copiando a imagem do monitor, por imagem | O menor possível, porque ele faz parte do tempo de cada quadro |
| session | A situação da conexão com o headset. Os controles só funcionam em `FOCUSED`. Outra situação aparece, por exemplo, com o menu do headset aberto | `FOCUSED` enquanto você joga |

Se o jogo engasgar ou o uso do processador estiver alto, troque para o perfil `performance` (o padrão é o `smooth`) e deixe o `capture.mipmaps` desligado (veja [Perfis](configuration.pt-BR.md)). O `vr-gyro-screen bench` compara os backends de captura no seu computador, sem o headset.

## 🚧 Limitações conhecidas

Estas são coisas que o app ainda não resolve. Não há conserto do seu lado, mas algumas podem ser amenizadas.

**O ponteiro do mouse não aparece no headset.** A captura copia a imagem da área de trabalho, e o Windows desenha o ponteiro do mouse à parte, por cima dessa imagem. O app ainda não desenha o ponteiro por conta própria, então ele fica de fora da tela no headset. O que ameniza: a maioria dos jogos esconde o ponteiro durante a partida e usa o controle nos menus, então você só sente falta dele na área de trabalho do Windows ou em programas que precisam do mouse.

**O quarto não aparece em volta da tela em alguns runtimes.** A linha é `background: this runtime does not offer passthrough to apps; using black`. O passthrough (mostrar o seu quarto pelas câmeras do headset) depende de o runtime deixar os apps usarem as câmeras. Quando ele não deixa, o app passa sozinho para o fundo preto e continua funcionando normalmente. O app não consegue ligar isso do lado dele. Para não ver mais a linha, ponha o `screen.background` em `auto` ou `black`.

**Detalhes finos cintilam mesmo com mipmaps ligados.** A linha é `the runtime refused N mipmap levels (...); continuing without`. Alguns runtimes não aceitam a imagem com mipmaps, então o app segue sem eles, e a imagem fica como com os mipmaps desligados: os detalhes finos podem cintilar. O que pode ajudar: uma tela maior na sua visão (`screen.width_m` maior ou uma distância menor) faz a imagem ser menos reduzida, e com isso cintila menos.

**A captura usa um pouco mais de processador em algumas placas de vídeo.** A linha é `capture: staying on the processor path (...)`. O método de captura mais barato precisa de um recurso de compartilhamento de textura do driver de vídeo. Quando o driver não oferece esse recurso, o app usa o método `direct`, que funciona igual e mostra a mesma imagem, com um pouco mais de uso do processador (veja [Backends de captura](configuration.pt-BR.md)). O que ajuda, se o processador estiver ocupado: o perfil `performance` mantém o trabalho de captura baixo.

## 🧪 Não testado

Só uma montagem foi testada: um headset Meta Quest com o Virtual Desktop e o runtime OpenXR dele. Outros headsets, outros runtimes OpenXR e outras placas de vídeo não foram testados. O custo da captura dentro do headset a 1440p e 90 Hz ainda não foi medido. Se algo falhar numa montagem assim, você está em terreno novo, e as linhas que o app imprime são o melhor ponto de partida para entender o que aconteceu.
