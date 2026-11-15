[English](configuration.md) | **Português**

# ⚙️ Configuração

Esta página explica cada opção do app: o que ela é, o que você percebe jogando quando muda, quando vale a pena mexer e um valor de exemplo. O app funciona sem nenhuma configuração, então você só precisa desta página quando algo não estiver do seu jeito. O jeito principal de mudar as opções é a janela de configuração, nas páginas **Tela**, **Movimento e atalhos** e **Botões** (veja o [uso](usage.pt-BR.md)); cada opção ali tem um botão **i** com a explicação.

O arquivo descrito abaixo é a alternativa: a janela grava nele, e você também pode editá-lo à mão. Salvar na janela reescreve o arquivo só com o que for diferente do padrão e guarda a versão anterior como `config.toml.bak`. Voltar ao [README](../README.pt-BR.md).

## 📍 Onde o arquivo fica

As opções ficam guardadas num arquivo de texto no formato TOML (um formato simples de `nome = valor`, uma opção por linha, agrupadas sob títulos entre colchetes, como `[gyro]`).

- Para começar, copie o [config.example.toml](../config.example.toml) para `%APPDATA%\vr-gyro-screen\config.toml` (cole `%APPDATA%\vr-gyro-screen` na barra de endereço do Explorador de Arquivos para abrir a pasta; se ela não existir, crie). Todos os valores do exemplo já são os padrões, então você só muda as linhas que interessam.
- Você também pode deixar o arquivo em qualquer lugar e iniciar o app com `vr-gyro-screen --config ARQUIVO`.
- Sem arquivo na pasta padrão, o app usa os padrões dele. Um arquivo passado com `--config` que não existe é um erro.
- O app confere o arquivo inteiro ao iniciar. Um nome que ele não conhece, um valor fora da faixa ou um nome de botão errado fazem o app parar com `configuration problem: ...` e uma descrição do que está errado, para nenhum erro de digitação passar despercebido. Nada fica aplicado pela metade.
- Opções passadas na linha de comando (como `--profile` ou `--distance`) valem mais que o arquivo.

O app também guarda um arquivo `screen.json` na mesma pasta. Ele tem a posição da tela que você ajustou por último dentro do headset (veja o [uso](usage.pt-BR.md)). Você não edita esse arquivo à mão: apagá-lo faz o app esquecer a posição salva.

## 🎚️ Perfis

Um perfil diz quantas vezes a tela do headset pega uma imagem nova do PC. O padrão pega todas as imagens, para a tela não ficar abaixo do que o jogo e o headset conseguem mostrar.

| Perfil | Imagens novas por segundo | O que você percebe |
|---|---|---|---|
| `smooth` (padrão) | todas as que o PC produz | O movimento na tela fica tão fluido quanto o jogo e o headset permitem. Usa um pouco mais do processador. Se o jogo começar a engasgar, troque para o `performance` |
| `performance` | no máximo 60 | O mais leve: deixa o máximo de força para o jogo |

**Os mipmaps não estão em nenhum perfil.** A imagem do monitor tem mais pixels do que a área que ela ocupa dentro do headset, então ela é reduzida no caminho. Mipmaps são cópias menores da imagem que deixam essa redução mais suave, mas prepará-las a cada imagem custa à placa de vídeo rajadas curtas que podem aparecer como engasgos no jogo. Ficam desligados, a não ser que você ligue à mão com `capture.mipmaps = true`.

**Qual valor vale.** Se o seu arquivo define `capture.mipmaps` ou `capture.max_fps`, esse valor vale mais que o perfil escrito no mesmo arquivo. A opção `--profile` da linha de comando é a exceção: ela aplica o perfil inteiro por cima do arquivo, inclusive esses dois valores.

Exemplo, no arquivo:

```toml
profile = "performance"
```

## 🧾 Opções

Resumo rápido. Cada opção é explicada em detalhe logo abaixo da tabela.

| Opção | Padrão | Valores aceitos |
|---|---|---|
| `profile` | `"smooth"` | `performance`, `smooth` |
| `screen.monitor` | `"auto"` | `auto`, um número ou parte do nome de um monitor |
| `screen.distance_m` | `2.0` | 0,8 a 6,0 |
| `screen.width_m` | `2.6` | 0,3 a 20,0 |
| `screen.background` | `"auto"` | `auto`, `passthrough`, `black` |
| `capture.backend` | `"auto"` | `auto`, `gpu`, `direct`, `dxcam` |
| `capture.mipmaps` | `false` | `true`, `false` |
| `capture.max_fps` | do perfil | número inteiro de 0 a 1000 |
| `gyro.hand` | `"right"` | `left`, `right` |
| `gyro.scale` | `1.0` | 0 a 20 |
| `gyro.deadzone_dps` | `1.5` | 0 a 90 |
| `gyro.keepalive` | `true` | `true`, `false` |
| `recenter.hold_s` | `1.0` | 0,2 a 10 |

No arquivo, a parte antes do ponto é o título do grupo, e a parte depois é a linha. Por exemplo, `gyro.scale` se escreve assim (no arquivo, o número usa ponto, não vírgula):

```toml
[gyro]
scale = 1.5
```

### A tela

**`screen.monitor`: qual monitor aparece no headset.** O app mostra um monitor do Windows na tela grande. Com `auto`, ele escolhe o monitor virtual que o Virtual Desktop cria (um monitor a mais que só existe no software, feito para o headset). Se não houver, escolhe um monitor que não seja o principal e, em último caso, o principal. Mude quando o monitor errado aparecer no headset. Rode `vr-gyro-screen monitors` para ver a lista: você pode usar o número que aparece antes de cada monitor ou parte do nome dele. Exemplo: `monitor = "1"`.

**`screen.distance_m`: a que distância a tela fica, em metros.** É a distância inicial entre você e a tela. Depois que você ajusta a distância dentro do headset (segurando Y e mexendo o analógico direito para os lados), o app salva esse ajuste, e a distância salva passa a valer mais que esta opção, porque é o que você escolheu por último.

Na janela de configurações você não precisa pensar nisso: o campo de distância mostra o último ajuste e o que ficar ali é o que vale. Pela linha de comando, para voltar ao valor do arquivo, apague o `screen.json` ou inicie o app com `--distance`. Exemplo: `distance_m = 2.5`.

**`screen.width_m`: a largura da tela, em metros.** A altura acompanha o formato do monitor, então um monitor 16:9 continua 16:9. Uma tela mais larga na mesma distância ocupa mais da sua visão, como sentar mais perto de uma TV. Mude se a imagem estiver pequena demais para ler ou grande demais para ver inteira. Exemplo: `width_m = 3.2`.

**`screen.background`: o que você vê em volta da tela.** `black` deixa a tela num espaço escuro e vazio. `passthrough` mostra o seu quarto pelas câmeras do headset. `auto` mostra o quarto quando for possível e preto quando não for. O quarto só aparece se o runtime (o software no PC que liga o app ao headset; aqui, o do Virtual Desktop) deixar os apps mostrarem as câmeras. Quando ele não deixa, o fundo fica preto. Exemplo: `background = "black"`.

### A captura

**`capture.backend`: como a imagem do monitor é copiada.** Muda só o quanto de processador o app usa; a imagem no headset é a mesma. Deixe em `auto`, a não ser que a página de solução de problemas mande trocar. As opções estão comparadas em [Backends de captura](#backends-de-captura), mais abaixo. Exemplo: `backend = "direct"`.

**`capture.mipmaps`: redução suave da imagem.** Ligado, os detalhes muito finos (letra pequena, grama) ficam mais estáveis quando você mexe a cabeça, mas a placa de vídeo trabalha em rajadas curtas que podem aparecer como engasgos no jogo. Fica desligado em todos os perfis; ligue só se os detalhes finos cintilarem e o jogo tiver força sobrando. Exemplo: `mipmaps = true`.

**`capture.max_fps`: o máximo de imagens novas por segundo.** Limita quantas vezes por segundo o app copia uma imagem nova do monitor. `0` copia uma a cada quadro que o headset mostra, o que é o mais fluido. Um número menor economiza processador, e o movimento rápido fica um pouco menos fluido quando o jogo roda mais rápido que o limite. Normalmente quem decide é o perfil. Exemplo: `max_fps = 72`.

### A mira por movimento

Estas opções mexem no giroscópio, o sensor de movimento do controle virtual que o jogo lê para mirar. A mira só funciona em jogos que têm mira por movimento (giroscópio) e reconhecem um controle DualShock 4.

**`gyro.hand`: qual mão mira.** O movimento deste controle vira o giroscópio do controle virtual. Mude se você mira com a mão esquerda. Exemplo: `hand = "left"`.

**`gyro.scale`: sensibilidade da mira dentro do app.** A velocidade com que a sua mão gira é multiplicada por este número antes de chegar ao jogo. Em `2.0`, um giro pequeno do pulso move a mira o dobro; em `0.5`, a metade. Ajuste a sensibilidade primeiro no jogo, porque o ajuste do próprio jogo costuma ser mais fino. Use esta opção só quando o ajuste do jogo não bastar. Exemplo: `scale = 1.5`.

**`gyro.deadzone_dps`: zona morta, para a mira ficar parada.** Zona morta é uma faixa pequena de movimento que é ignorada de propósito. Mesmo parada, a mão treme um pouco, e o rastreamento do headset soma um ruído pequeno. Quando a sua mão gira mais devagar que este valor, em graus por segundo, o app manda "nenhum movimento", e a mira não treme.

Aumente se a mira tremer ou escorregar com a mão parada. Diminua se a mira lenta e precisa parecer travada ou não responder, porque movimentos mais lentos que o limite são descartados. O limite é aplicado antes do `gyro.scale`. Exemplo: `deadzone_dps = 3.0`.

**`gyro.keepalive`: mantém o sensor de movimento "acordado" para o jogo.** Alguns jogos reiniciam o sensor de movimento quando o giroscópio informa exatamente o mesmo valor por um tempo, o que acontece quando a sua mão está parada. Com esta opção ligada, o app soma ao giroscópio um vaivém minúsculo a cada envio, então o valor nunca se repete igualzinho. O movimento é pequeno demais para ser visto e se anula na média, então a mira fica onde está. Deixe ligado. Desligue só para conferir se um jogo específico se comporta diferente sem ele.

Detalhe técnico: o vaivém é de uma unidade do sensor (1/16 de grau por segundo), com o sinal trocando a cada envio. Exemplo: `keepalive = false`.

### Recentralizar

**`recenter.hold_s`: quanto tempo segurar os dois cliques dos analógicos.** Apertar os dois analógicos para baixo (como um botão) e segurar traz a tela para a frente de onde você está olhando. Esta opção é quantos segundos você precisa segurar até isso acontecer. Aumente se você recentraliza sem querer durante o jogo; diminua se a espera incomodar. No arquivo, ela fica sob `[recenter]`. Exemplo: `hold_s = 1.5`.

### Backends de captura

Backend é o método usado para copiar a imagem do monitor. Os três geram a mesma imagem (isso foi conferido pixel a pixel); o que muda é o trabalho do processador.

| Backend | Como funciona | Uso de processador medido num monitor 1080p a 90 cópias por segundo |
|---|---|---|
| `gpu` | A imagem fica o tempo todo na placa de vídeo. Precisa de um recurso de compartilhamento de textura do driver de vídeo (`WGL_NV_DX_interop2`) | Cerca de 7% de um núcleo |
| `direct` | A imagem passa uma vez pela memória do computador a cada imagem nova | Cerca de 16% de um núcleo |
| `dxcam` | Usa a biblioteca externa `dxcam`, que mantém uma tarefa em segundo plano e faz várias cópias por imagem. Precisa de uma instalação a mais: `pip install ".[dxcam]"` | Cerca de 47% de um núcleo |

Com `auto`, o app tenta `gpu`. Se o driver de vídeo não oferecer o compartilhamento de textura, ele usa `direct` e imprime uma linha avisando. O `dxcam` só é usado quando você pede pelo nome.

> [!NOTE]
> Estes números vêm de `vr-gyro-screen bench` num monitor 1080p. A captura a 1440p e 90 Hz dentro do headset **ainda não foi medida**. Rode `vr-gyro-screen bench` no seu computador para comparar os backends nele.

## 🎮 Mapeamento dos botões

O mapeamento diz qual botão do controle vira qual botão do controle virtual. Quando o arquivo é carregado, o app confere cada nome; um nome errado faz o app parar com uma mensagem que lista o que está errado.

**Entradas do controle** (os nomes dos botões dos controles do headset):

| Nome | Botão |
|---|---|
| `a`, `b` | A e B, no controle direito |
| `x`, `y` | X e Y, no controle esquerdo |
| `menu` | O botão de menu, no controle esquerdo |
| `left_stick_click`, `right_stick_click` | Apertar o analógico para baixo, como um botão |
| `left_trigger`, `right_trigger` | Os gatilhos, embaixo do dedo indicador |
| `left_squeeze`, `right_squeeze` | Os grips, na lateral de cada controle, embaixo do dedo médio |

**Botões do controle virtual** (os nomes dos botões do DualShock 4 virtual):

| Nome | Botão |
|---|---|
| `CROSS`, `CIRCLE`, `SQUARE`, `TRIANGLE` | Os quatro botões de símbolo (xis, círculo, quadrado e triângulo): embaixo, à direita, à esquerda e em cima |
| `SHOULDER_LEFT`, `SHOULDER_RIGHT` | Os botões de ombro esquerdo e direito (acima dos gatilhos) |
| `THUMB_LEFT`, `THUMB_RIGHT` | Apertar o analógico esquerdo ou o direito para baixo |
| `OPTIONS`, `SHARE` | Os botões pequenos à direita e à esquerda do touchpad |
| `PS` | O botão redondo do logotipo, no meio |
| `TOUCHPAD` | Um clique no touchpad |

### `[buttons]`

Cada linha transforma um botão do controle num botão do controle virtual. Os padrões seguem a posição dos botões, então o botão de baixo continua embaixo:

| Entrada | Botão |
|---|---|
| `a` | `CROSS` |
| `b` | `CIRCLE` |
| `x` | `SQUARE` |
| `left_squeeze` | `SHOULDER_LEFT` |
| `right_squeeze` | `SHOULDER_RIGHT` |
| `left_stick_click` | `THUMB_LEFT` |
| `right_stick_click` | `THUMB_RIGHT` |
| `menu` | `OPTIONS` |

O `y` não está na tabela porque ele é a tecla de combinação (veja `[combo]` abaixo). Atenção: se você escrever um grupo `[buttons]` no seu arquivo, ele substitui a tabela inteira, e não só as linhas que você escreveu. Liste todos os botões que quiser, inclusive os que continuam iguais.

### `[triggers]`

| Opção | Padrão | O que faz |
|---|---|---|
| `left` | `"left_trigger"` | Qual entrada do controle aciona o gatilho esquerdo do controle virtual |
| `right` | `"right_trigger"` | Qual entrada do controle aciona o gatilho direito do controle virtual |

Os gatilhos do controle virtual são analógicos: o jogo sabe o quanto você apertou, e não só se apertou. Por isso só entradas analógicas são aceitas aqui: `left_trigger`, `right_trigger`, `left_squeeze` ou `right_squeeze`. Exemplo: `left = "left_squeeze"` faz o grip esquerdo funcionar como gatilho esquerdo.

Dois limites são fixos. Além do quanto está apertado, o controle virtual também informa cada gatilho como botão apertado, para jogos que só olham isso; isso acontece a partir de 30% do curso. Um grip ou gatilho usado como botão comum em `[buttons]` conta como apertado a partir de 50% do curso.

### `[combo]`

Os controles do headset têm menos botões que um controle de videogame. Para chegar aos que faltam, um botão funciona como tecla de combinação, como o Shift do teclado: segurado junto com outro botão ou com um analógico, ele vira outra coisa. Por padrão a tecla é o Y.

| Opção | Padrão | O que faz |
|---|---|---|
| `key` | `"y"` | Qual botão é a tecla de combinação. `"none"` desliga as combinações. A tecla não pode aparecer também em `[buttons]` nem em `[combo.with]` |
| `solo` | `"TRIANGLE"` | O que a tecla envia quando você aperta só ela. `"none"` para nada |
| `solo_delay_s` | `0.25` | Quanto tempo, em segundos, o app espera para decidir se você está apertando só a tecla. Faixa de 0 a 5 |
| `dpad` | `true` | Tecla + analógico esquerdo vira o direcional (os quatro botões de seta) |
| `screen_adjust` | `true` | Tecla + analógico direito move a tela dentro do headset (para cima e para baixo, mais perto e mais longe). Isso nunca chega ao jogo |
| `with` | `{ x = "SHARE" }` | Tecla + outro botão envia um botão do controle virtual. Escrito como grupo próprio, `[combo.with]` |

**Como funciona a tecla sozinha.** Quando você aperta o Y, o app ainda não sabe se você vai combinar com outra coisa, então ele espera. Um aperto rápido (mais curto que `solo_delay_s`) chega ao jogo como um toque curto quando você solta. Se você segurar por mais tempo sem combinar, o botão solo fica apertado enquanto você segurar.

Na prática: diminua o `solo_delay_s` se o TRIANGLE parecer atrasado quando você segura o Y; aumente se o TRIANGLE disparar sem querer quando você começa uma combinação devagar. Com `0`, o TRIANGLE é apertado na hora, mas também chega ao jogo no começo de toda combinação.

**Combinação com outro botão.** Enquanto a tecla está segurada, um botão listado em `[combo.with]` envia o botão escrito ali, no lugar do normal dele. Por padrão, Y + X envia SHARE (e não SQUARE).

**Desligar as combinações.** Com `key = "none"`, o Y deixa de ser tecla de combinação, e o direcional e o ajuste da tela pela tecla também param de funcionar. O Y passa a não fazer nada até você colocá-lo em `[buttons]`, por exemplo `y = "TRIANGLE"`.

Exemplo, para colocar também o botão PS em Y + menu (mantenha o `x = "SHARE"`, porque este grupo também substitui o padrão inteiro):

```toml
[combo.with]
x = "SHARE"
menu = "PS"
```

## 🧪 Fora do arquivo

- Os comandos `window` e `bench` têm opções próprias na linha de comando, listadas no [uso](usage.pt-BR.md). Elas não ficam salvas no arquivo.
- A posição salva da tela fica no `screen.json`, e não neste arquivo (veja [Onde o arquivo fica](#-onde-o-arquivo-fica)).
