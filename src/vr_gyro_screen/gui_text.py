"""Texts of the settings window, in English and in Brazilian Portuguese.

Every option has a short label and a longer "help_" text. The first sentence of the help says
what the option is for and is always visible under the label; the rest opens from the
information button next to it.
"""

from __future__ import annotations

import json
import os
import sys

from .config import data_dir

LANGUAGE_VARIABLE = "VR_GYRO_SCREEN_LANG"  # "en" or "pt", to force a language
LANGUAGE_CHOICES = ("auto", "pt", "en")
_PREFERENCES_FILE = "window.json"
_PORTUGUESE = 0x16  # primary language identifier used by Windows

EN: dict[str, str] = {
    "title": "VR Gyro Screen",
    "byline": "by Scarlet Modder",
    "version": "version {version}",
    "tab_start": "Start",
    "tab_screen": "Screen",
    "tab_controller": "Motion and shortcuts",
    "tab_buttons": "Buttons",
    "left_controller": "Left controller",
    "right_controller": "Right controller",
    "section_image": "Image",
    "section_place": "Size and position",
    "advanced": "Advanced",
    "steps_title": "How to use",
    "step_1": "Check that everything this program needs is installed.",
    "step_2": "Turn the headset on and connect it to this PC with Virtual Desktop.",
    "step_3": "Press Start and put the headset on. The screen shows up in front of you and games see a gamepad.",
    "language": "Language",
    "language_auto": "Same as Windows",
    "language_pt": "Português (Brasil)",
    "language_en": "English",
    "more_info": "What is this?",
    "state": "Status",
    "requirements": "What this program needs",
    "check_gamepad_driver": "Virtual gamepad driver (ViGEmBus)",
    "check_openxr_runtime": "A program that connects the headset to this PC",
    "check_virtual_desktop_runtime": "Virtual Desktop chosen as that program",
    "help_check_gamepad_driver": "ViGEmBus is a free driver that lets programs create a pretend gamepad. "
    "Games see that gamepad as if it were plugged into the PC. Without it, the game receives no buttons "
    "and no motion.",
    "help_check_openxr_runtime": "This program shows the screen through the app that links your headset to the PC. The "
    "technical name of that app is OpenXR runtime, and Virtual Desktop Streamer installs one.",
    "help_check_virtual_desktop_runtime": "A PC can have more than one of those apps installed, but only one "
    "is active. This program was made for Virtual Desktop. To make it the active one, open Virtual Desktop "
    "Streamer on the PC, go to Options and choose VDXR as the OpenXR runtime.",
    "found": "found",
    "missing": "not found",
    "active_runtime": "active: {name}",
    "open_site": "Open the official site",
    "check_again": "Check again",
    "requirements_note": "This program installs none of these for you. Each button opens the site of whoever makes it.",
    "start": "Start",
    "stop": "Stop",
    "state_stopped": "Stopped. Press Start when the headset is connected to the PC.",
    "state_running": "Running. Put the headset on.",
    "state_stopping": "Closing...",
    "state_failed": "Closed with a problem. See the messages below.",
    "how_to_title": "Inside the headset",
    "how_to": "Bring the screen back in front of you: press and hold both sticks (click them like buttons) "
    "for about a second.\n"
    "Move the screen: hold the combination button (Y by default) and push the right stick. Up and down "
    "raise and lower it, left and right bring it closer or farther.",
    "messages": "Messages from the program",
    "help_messages": "What the program is doing, line by line. If something goes wrong, the reason shows "
    "up here. Copy diagnostics puts these messages and a summary of your setup on the clipboard, ready to "
    "paste when asking for help.",
    "copy_diagnostics": "Copy diagnostics",
    "copied": "Copied",
    "missing_title": "Something seems to be missing",
    "missing_question": "These were not found:\n\n{items}\n\nStart anyway?",
    "monitor": "Monitor shown in the headset",
    "help_monitor": "Which of the PC's monitors appears on the big screen. Automatic picks the virtual "
    "monitor created by Virtual Desktop, so the game can run there while your real monitor stays free. If "
    "there is no virtual monitor, it picks a second monitor, then the main one.",
    "monitor_auto": "Automatic (the Virtual Desktop virtual monitor)",
    "monitor_saved": "{name} (saved, not connected now)",
    "refresh": "Refresh the list",
    "profile": "Smoothness and performance",
    "help_profile": "How often the screen in the headset takes a new image from the PC. Smooth takes every "
    "image the PC produces, so motion on the screen is as fluid as the game and the headset allow: it is "
    "the recommended choice. Light takes one at most 60 times per second and leaves the most power for the "
    "game. If the game starts to stutter with Smooth, change to Light.",
    "profile_performance": "Light: at most 60 images per second",
    "profile_smooth": "Smooth (recommended): shows every image",
    "distance": "Distance to the screen (metres)",
    "help_distance": "How far in front of you the screen floats. You can also change it inside the "
    "headset (combination button + right stick); the last distance used there is remembered.",
    "width": "Width of the screen (metres)",
    "help_width": "How wide the screen is in the virtual room. The height follows the shape of the monitor. "
    "At 2 metres away, 2.6 metres wide feels like a cinema seat in the middle rows.",
    "background": "Around the screen",
    "help_background": "What you see around the screen. Your room uses the headset cameras to show the "
    "real room (passthrough). Black hides everything. Automatic uses your room when the headset allows it "
    "and black otherwise.",
    "background_auto": "Automatic (your room when the headset allows it)",
    "background_passthrough": "Your room (headset cameras)",
    "background_black": "Black",
    "backend": "How the monitor image is captured",
    "help_backend": "Leave on Automatic unless the screen stays black or freezes. Graphics card is the "
    "fastest. Direct copy is slower but works on more computers.",
    "backend_auto": "Automatic",
    "backend_gpu": "Graphics card (fastest)",
    "backend_direct": "Direct copy (most compatible)",
    "backend_dxcam": "dxcam (needs the optional package)",
    "motion": "Motion sensor (aiming by moving your hand)",
    "hand": "Hand that aims",
    "help_hand": "The controller whose movement becomes the gamepad's motion sensor. Games that support "
    "motion aiming follow this hand.",
    "hand_left": "Left",
    "hand_right": "Right",
    "scale": "Sensitivity",
    "help_scale": "How much the aim moves when your hand moves. 1 passes the movement as it is, 2 doubles it "
    "(less hand movement for the same aim) and 0.5 halves it. 0 turns motion aiming off.",
    "deadzone": "Ignore hand tremor below (degrees per second)",
    "help_deadzone": "Hand movements slower than this are ignored, so the aim does not drift by itself. Nobody "
    "holds a hand perfectly still. Raise it if the aim trembles; lower it if slow, careful "
    "movements are being ignored.",
    "keepalive": "Keep the sensor awake while the hand is still",
    "help_keepalive": "Stops some games from switching motion aiming off when your hand is still. Those games think "
    "the sensor was disconnected when it reports exactly the same value for a while. With this on, "
    "the program adds a tiny back and forth movement, too small to move the aim, so the game keeps "
    "listening. Turn it off only if a game behaves oddly with it.",
    "buttons": "Buttons",
    "buttons_intro": "Each row is a button on the headset controllers. Choose which gamepad button the "
    "game receives when you press it.",
    "column_input": "On the headset controller",
    "column_alone": "Gamepad button",
    "column_combo": "While holding the combination button",
    "help_column_alone": "The gamepad button the game receives when you press this button by itself. "
    "The names are the usual ones on a gamepad, with the position in parentheses, because games "
    "may show letters or symbols.",
    "help_column_combo": "A second function for the same button. The headset controllers have fewer buttons than a "
    "gamepad, so one button is set aside as the combination button (you choose which one in Motion "
    "and shortcuts). While you hold it, the other buttons send what is chosen in this column "
    "instead. Leave No function where you do not need a second function.",
    "nothing": "No function",
    "triggers": "Triggers",
    "help_triggers": "Which controller input works as this gamepad trigger. The triggers are L2 and R2 on the "
    "gamepad, and they are analog: pressing halfway counts as half.",
    "trigger_left": "Left trigger (L2)",
    "trigger_right": "Right trigger (R2)",
    "combo": "Combination button",
    "combo_intro": "A button that gives the others a second function while you hold it, like Shift on a keyboard.",
    "combo_key": "Which button it is",
    "is_combo": "combination button",
    "help_combo_key": "The headset controller button that works as the combination button. Choose No "
    "function to turn combinations off.",
    "combo_solo": "Pressed by itself, it sends",
    "help_combo_solo": "What the combination button sends when you use it by itself. A quick press, or holding it "
    "without pressing anything else, sends this gamepad button, so it still works as a normal "
    "button.",
    "combo_delay": "Wait before it counts as pressed by itself (seconds)",
    "help_combo_delay": "How long the program waits to see if you will press another button. If you do not, the "
    "combination button starts sending its own button. Shorter feels snappier, but can send the "
    "button by accident when you were starting a combination.",
    "combo_dpad": "Combination + left stick works as the arrows",
    "help_combo_dpad": "Holding the combination button and pushing the left stick presses the arrows of the gamepad. "
    "The headset controllers have no directional pad of their own, so this is how you reach it.",
    "combo_screen": "Combination + right stick moves the screen",
    "help_combo_screen": "Holding the combination button and pushing the right stick moves the screen in the headset. "
    "Up and down raise and lower it, left and right bring it closer or farther. The game does not "
    "receive that movement.",
    "recenter": "Hold both stick clicks to recenter (seconds)",
    "help_recenter": "Pressing both sticks down (as buttons) for this long brings the screen back in "
    "front of where you are looking. Useful after changing position.",
    "save": "Save",
    "defaults": "Restore defaults",
    "saved": "Saved. It takes effect the next time you press Start.",
    "saved_running": "Saved. Press Apply now to use the new settings.",
    "apply_now": "Apply now",
    "running_note": "Running: changes are used after you save and apply them.",
    "state_restarting": "Restarting with the new settings...",
    "invalid_title": "These settings cannot be saved",
    "load_problem_title": "The settings file has a problem",
    "load_problem": "{error}\n\nThe built-in defaults are shown. Saving keeps the old file next to the new one, "
    "with .bak at the end of its name.",
    "input_a": "A",
    "input_b": "B",
    "input_x": "X",
    "input_y": "Y",
    "input_menu": "Menu (left controller)",
    "input_left_stick_click": "Left stick click",
    "input_right_stick_click": "Right stick click",
    "input_left_trigger": "Left trigger (index finger)",
    "input_right_trigger": "Right trigger (index finger)",
    "input_left_squeeze": "Left grip (side button)",
    "input_right_squeeze": "Right grip (side button)",
    "pad_CROSS": "Cross (bottom button)",
    "pad_CIRCLE": "Circle (right button)",
    "pad_SQUARE": "Square (left button)",
    "pad_TRIANGLE": "Triangle (top button)",
    "pad_SHOULDER_LEFT": "L1 (left shoulder)",
    "pad_SHOULDER_RIGHT": "R1 (right shoulder)",
    "pad_THUMB_LEFT": "L3 (left stick click)",
    "pad_THUMB_RIGHT": "R3 (right stick click)",
    "pad_OPTIONS": "Options (Start)",
    "pad_SHARE": "Share (Select)",
    "pad_PS": "PS (home button)",
    "pad_TOUCHPAD": "Touchpad click",
}

PT: dict[str, str] = {
    "title": "VR Gyro Screen",
    "byline": "por Scarlet Modder",
    "version": "versão {version}",
    "tab_start": "Início",
    "tab_screen": "Tela",
    "tab_controller": "Movimento e atalhos",
    "tab_buttons": "Botões",
    "left_controller": "Controle esquerdo",
    "right_controller": "Controle direito",
    "section_image": "Imagem",
    "section_place": "Tamanho e posição",
    "advanced": "Avançado",
    "steps_title": "Como usar",
    "step_1": "Confira se tudo o que este programa precisa está instalado.",
    "step_2": "Ligue o headset e conecte a este PC pelo Virtual Desktop.",
    "step_3": "Aperte Iniciar e coloque o headset. A tela aparece na sua frente e o jogo enxerga um controle.",
    "language": "Idioma",
    "language_auto": "O mesmo do Windows",
    "language_pt": "Português (Brasil)",
    "language_en": "English",
    "more_info": "O que é isto?",
    "state": "Situação",
    "requirements": "O que este programa precisa",
    "check_gamepad_driver": "Driver de controle virtual (ViGEmBus)",
    "check_openxr_runtime": "Um programa que liga o headset a este PC",
    "check_virtual_desktop_runtime": "Virtual Desktop escolhido como esse programa",
    "help_check_gamepad_driver": "O ViGEmBus é um driver gratuito que deixa programas criarem um controle de "
    "mentira. O jogo enxerga esse controle como se estivesse ligado no PC. Sem ele, o jogo não recebe "
    "nem os botões nem o movimento.",
    "help_check_openxr_runtime": "Este programa mostra a tela usando o aplicativo que liga o seu headset ao PC. "
    "O nome técnico desse aplicativo é runtime OpenXR, e o Virtual Desktop Streamer instala um.",
    "help_check_virtual_desktop_runtime": "Um PC pode ter mais de um desses aplicativos instalados, mas só "
    "um fica ativo. Este programa foi feito para o Virtual Desktop. Para ativar: abra o Virtual Desktop "
    "Streamer no PC, entre em Options e escolha VDXR em OpenXR Runtime.",
    "found": "encontrado",
    "missing": "não encontrado",
    "active_runtime": "ativo: {name}",
    "open_site": "Abrir o site oficial",
    "check_again": "Conferir de novo",
    "requirements_note": "Este programa não instala nenhum deles por você. Cada botão abre o site de quem faz.",
    "start": "Iniciar",
    "stop": "Parar",
    "state_stopped": "Parado. Aperte Iniciar quando o headset estiver conectado ao PC.",
    "state_running": "Rodando. Coloque o headset.",
    "state_stopping": "Fechando...",
    "state_failed": "Fechou com um problema. Veja as mensagens abaixo.",
    "how_to_title": "Dentro do headset",
    "how_to": "Trazer a tela de volta para a sua frente: aperte e segure os dois analógicos (clicando neles "
    "como botões) por cerca de um segundo.\n"
    "Mover a tela: segure o botão de combinação (o Y, por padrão) e empurre o analógico direito. Para "
    "cima e para baixo sobe e desce a tela; para os lados aproxima ou afasta.",
    "messages": "Mensagens do programa",
    "help_messages": "O que o programa está fazendo, linha por linha. Se algo der errado, o motivo aparece "
    "aqui. O botão Copiar diagnóstico copia essas mensagens e um resumo da sua instalação, prontos para "
    "colar ao pedir ajuda.",
    "copy_diagnostics": "Copiar diagnóstico",
    "copied": "Copiado",
    "missing_title": "Parece que falta alguma coisa",
    "missing_question": "Não foi encontrado:\n\n{items}\n\nIniciar mesmo assim?",
    "monitor": "Monitor mostrado no headset",
    "help_monitor": "Qual monitor do PC aparece na tela grande. Automático escolhe o monitor virtual que o "
    "Virtual Desktop cria, assim o jogo roda nele e o seu monitor de verdade fica livre. Se não houver "
    "monitor virtual, escolhe um segundo monitor e, por último, o principal.",
    "monitor_auto": "Automático (o monitor virtual do Virtual Desktop)",
    "monitor_saved": "{name} (salvo, não está conectado agora)",
    "refresh": "Atualizar a lista",
    "profile": "Fluidez e desempenho",
    "help_profile": "Quantas vezes a tela do headset pega uma imagem nova do PC. Fluido pega todas as imagens "
    "que o PC produz, então o movimento na tela fica tão suave quanto o jogo e o headset permitem: é a "
    "escolha recomendada. Leve pega no máximo 60 por segundo e deixa o máximo de força para o jogo. Se o "
    "jogo começar a engasgar com o Fluido, troque para o Leve.",
    "profile_performance": "Leve: no máximo 60 imagens por segundo",
    "profile_smooth": "Fluido (recomendado): mostra todas as imagens",
    "distance": "Distância até a tela (metros)",
    "help_distance": "A que distância a tela flutua na sua frente. Dá para mudar também dentro do headset "
    "(botão de combinação + analógico direito); a última distância usada lá fica guardada.",
    "width": "Largura da tela (metros)",
    "help_width": "A largura da tela na sala virtual. A altura acompanha o formato do monitor. A 2 metros "
    "de distância, 2,6 metros de largura dá a sensação de uma poltrona no meio do cinema.",
    "background": "Em volta da tela",
    "help_background": "O que você vê ao redor da tela. A sua sala usa as câmeras do headset para mostrar "
    "o ambiente de verdade (passthrough). Preto esconde tudo. Automático usa a sua sala quando o "
    "headset permite e preto quando não permite.",
    "background_auto": "Automático (a sua sala, quando o headset permite)",
    "background_passthrough": "A sua sala (câmeras do headset)",
    "background_black": "Preto",
    "backend": "Como a imagem do monitor é capturada",
    "help_backend": "Deixe em Automático, a não ser que a tela fique preta ou congelada. Placa de vídeo é "
    "o mais rápido. Cópia direta é mais lenta, mas funciona em mais computadores.",
    "backend_auto": "Automático",
    "backend_gpu": "Placa de vídeo (mais rápido)",
    "backend_direct": "Cópia direta (mais compatível)",
    "backend_dxcam": "dxcam (precisa do pacote opcional)",
    "motion": "Sensor de movimento (mirar mexendo a mão)",
    "hand": "Mão que mira",
    "help_hand": "O controle cujo movimento vira o sensor de movimento do gamepad. Jogos que aceitam mira "
    "por movimento acompanham essa mão.",
    "hand_left": "Esquerda",
    "hand_right": "Direita",
    "scale": "Sensibilidade",
    "help_scale": "Quanto a mira anda quando a sua mão se mexe. 1 passa o movimento como ele é, 2 dobra (menos "
    "movimento da mão para a mesma mira) e 0,5 reduz pela metade. 0 desliga a mira por movimento.",
    "deadzone": "Ignorar tremor da mão abaixo de (graus por segundo)",
    "help_deadzone": "Movimentos da mão mais lentos que este valor são ignorados, para a mira não andar sozinha. "
    "Ninguém segura a mão totalmente parada. Aumente se a mira treme; diminua se movimentos lentos "
    "e cuidadosos estão sendo ignorados.",
    "keepalive": "Manter o sensor acordado com a mão parada",
    "help_keepalive": "Evita que alguns jogos desliguem a mira por movimento quando a sua mão fica parada. Esses "
    "jogos acham que o sensor foi desconectado quando ele manda exatamente o mesmo valor por um "
    "tempo. Com esta opção ligada, o programa soma um vai e vem minúsculo, pequeno demais para "
    "mexer a mira, e o jogo continua acompanhando. Desligue só se algum jogo se comportar de forma "
    "estranha.",
    "buttons": "Botões",
    "buttons_intro": "Cada linha é um botão dos controles do headset. Escolha qual botão do gamepad o jogo "
    "recebe quando você aperta.",
    "column_input": "No controle do headset",
    "column_alone": "Botão do gamepad",
    "column_combo": "Segurando o botão de combinação",
    "help_column_alone": "O botão do gamepad que o jogo recebe quando você aperta este botão sozinho. Os "
    "nomes são os mais comuns em gamepads, com a posição entre parênteses, porque o jogo pode mostrar "
    "letras ou símbolos.",
    "help_column_combo": "Uma segunda função para o mesmo botão. Os controles do headset têm menos botões que um "
    "gamepad, então um botão fica reservado como botão de combinação (você escolhe qual na página "
    "Movimento e atalhos). Enquanto você segura esse botão, os outros mandam o que estiver "
    "escolhido nesta coluna. Deixe Sem função onde você não precisa de segunda função.",
    "nothing": "Sem função",
    "triggers": "Gatilhos",
    "help_triggers": "Qual entrada do controle funciona como este gatilho do gamepad. Os gatilhos são o L2 e o R2 "
    "do gamepad, e são analógicos: apertar até a metade vale metade.",
    "trigger_left": "Gatilho esquerdo (L2)",
    "trigger_right": "Gatilho direito (R2)",
    "combo": "Botão de combinação",
    "combo_intro": "Um botão que dá uma segunda função aos outros enquanto você o segura, como o Shift do teclado.",
    "combo_key": "Qual botão é",
    "is_combo": "botão de combinação",
    "help_combo_key": "O botão do controle do headset que funciona como botão de combinação. Escolha Sem "
    "função para desligar as combinações.",
    "combo_solo": "Apertado sozinho, ele manda",
    "help_combo_solo": "O que o botão de combinação manda quando é usado sozinho. Um toque rápido, ou segurar sem "
    "apertar mais nada, manda este botão do gamepad, então ele continua servindo como botão comum.",
    "combo_delay": "Espera até valer como apertado sozinho (segundos)",
    "help_combo_delay": "Quanto tempo o programa espera para ver se você vai apertar outro botão. Se não apertar, o "
    "botão de combinação passa a mandar o botão próprio. Um tempo menor responde mais rápido, mas "
    "pode mandar o botão sem querer quando você ia começar uma combinação.",
    "combo_dpad": "Combinação + analógico esquerdo vira as setas",
    "help_combo_dpad": "Segurar o botão de combinação e empurrar o analógico esquerdo aperta as setas do gamepad. Os "
    "controles do headset não têm setas próprias, então é assim que você chega nelas.",
    "combo_screen": "Combinação + analógico direito move a tela",
    "help_combo_screen": "Segurar o botão de combinação e empurrar o analógico direito move a tela dentro do headset. "
    "Para cima e para baixo sobe e desce; para os lados aproxima ou afasta. O jogo não recebe esse "
    "movimento.",
    "recenter": "Segurar os dois analógicos para recentralizar (segundos)",
    "help_recenter": "Segurar os dois analógicos apertados (como botões) por este tempo traz a tela de volta para a "
    "sua frente. Útil depois de mudar de posição.",
    "save": "Salvar",
    "defaults": "Restaurar o padrão",
    "saved": "Salvo. Passa a valer na próxima vez que você apertar Iniciar.",
    "saved_running": "Salvo. Aperte Aplicar agora para usar as novas configurações.",
    "apply_now": "Aplicar agora",
    "running_note": "Rodando: as mudanças passam a valer depois de salvar e aplicar.",
    "state_restarting": "Reiniciando com as novas configurações...",
    "invalid_title": "Não foi possível salvar estas configurações",
    "load_problem_title": "O arquivo de configurações tem um problema",
    "load_problem": "{error}\n\nA janela mostra o padrão do programa. Ao salvar, o arquivo antigo fica guardado "
    "ao lado do novo, com .bak no fim do nome.",
    "input_a": "A",
    "input_b": "B",
    "input_x": "X",
    "input_y": "Y",
    "input_menu": "Menu (controle esquerdo)",
    "input_left_stick_click": "Clique do analógico esquerdo",
    "input_right_stick_click": "Clique do analógico direito",
    "input_left_trigger": "Gatilho esquerdo (dedo indicador)",
    "input_right_trigger": "Gatilho direito (dedo indicador)",
    "input_left_squeeze": "Botão lateral esquerdo (grip)",
    "input_right_squeeze": "Botão lateral direito (grip)",
    "pad_CROSS": "Xis (botão de baixo)",
    "pad_CIRCLE": "Círculo (botão da direita)",
    "pad_SQUARE": "Quadrado (botão da esquerda)",
    "pad_TRIANGLE": "Triângulo (botão de cima)",
    "pad_SHOULDER_LEFT": "L1 (ombro esquerdo)",
    "pad_SHOULDER_RIGHT": "R1 (ombro direito)",
    "pad_THUMB_LEFT": "L3 (clique do analógico esquerdo)",
    "pad_THUMB_RIGHT": "R3 (clique do analógico direito)",
    "pad_OPTIONS": "Options (Start)",
    "pad_SHARE": "Share (Select)",
    "pad_PS": "PS (botão central)",
    "pad_TOUCHPAD": "Clique do touchpad",
}


def language_choice() -> str:
    """The language picked in the window: "auto", "pt" or "en"."""
    try:
        saved = json.loads((data_dir() / _PREFERENCES_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "auto"
    choice = saved.get("language") if isinstance(saved, dict) else None
    return choice if choice in LANGUAGE_CHOICES else "auto"


def save_language_choice(choice: str) -> None:
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / _PREFERENCES_FILE).write_text(json.dumps({"language": choice}) + "\n", encoding="utf-8")


def pick_language() -> dict[str, str]:
    """The language chosen in the window; without a choice, Portuguese when Windows is in Portuguese."""
    forced = os.environ.get(LANGUAGE_VARIABLE, "").strip().lower()
    choice = forced if forced in ("en", "pt") else language_choice()
    if choice in ("en", "pt"):
        return PT if choice == "pt" else EN
    if sys.platform == "win32":
        import ctypes

        if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == _PORTUGUESE:
            return PT
    return EN


def summary(help_text: str) -> str:
    """The first sentence of a help text: what is always shown under the option's name."""
    first, separator, _rest = help_text.partition(". ")
    return first + "." if separator else help_text


def details(help_text: str) -> str:
    """What comes after the first sentence: shown when the information button is pressed."""
    return help_text[len(summary(help_text)) :].strip()
