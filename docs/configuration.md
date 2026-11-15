**English** | [Português](configuration.pt-BR.md)

# ⚙️ Configuration

This page explains every option of the app: what it is, what you notice while playing when you change it, when it is worth changing, and an example value. The app works without any configuration, so you only need this page when something does not suit you. The main way to change the options is the settings window, on its **Screen**, **Motion and shortcuts** and **Buttons** pages (see [usage](usage.md)); each option there has an **i** button with its explanation.

The file described below is the alternative: the window saves into it, and you can also edit it by hand. Saving in the window rewrites the file with only what differs from the defaults, and keeps the previous version as `config.toml.bak`. Back to the [README](../README.md).

## 📍 Where the file goes

The options are saved in a text file in the TOML format (a simple `name = value` format, one option per line, grouped under titles in square brackets such as `[gyro]`).

- To start, copy [config.example.toml](../config.example.toml) to `%APPDATA%\vr-gyro-screen\config.toml` (paste `%APPDATA%\vr-gyro-screen` in the address bar of the File Explorer to open the folder; create it if it does not exist). Every value in the example is already the default, so you only change the lines you care about.
- You can also keep the file anywhere and start the app with `vr-gyro-screen --config FILE`.
- Without a file in the default folder, the app uses its built-in defaults. A file passed with `--config` that does not exist is an error.
- The app checks the whole file when it starts. A name it does not know, a value out of range or a wrong button name stops it with `configuration problem: ...` and a description of what is wrong, so a typo never goes unnoticed. Nothing is half applied.
- Options given on the command line (such as `--profile` or `--distance`) win over the file.

The app also keeps a `screen.json` file in the same folder. It holds the screen position you last set inside the headset (see [usage](usage.md)). You do not edit it by hand: deleting it makes the app forget the saved position.

## 🎚️ Profiles

A profile says how often the screen in the headset takes a new image from the PC. The default takes every image, so the screen is not held below what the game and the headset can show.

| Profile | New images per second | What you notice |
|---|---|---|---|
| `smooth` (default) | every one the PC produces | Motion on the screen is as fluid as the game and the headset allow. Uses a little more of the processor. If the game starts to stutter, change to `performance` |
| `performance` | at most 60 | The lightest: leaves the most power for the game |

**Mipmaps are in no profile.** The monitor image has more pixels than the area it covers inside the headset, so it is shrunk on the way. Mipmaps are smaller copies of the image that make this shrinking smoother, but building them for every image costs the graphics card short bursts that can show up as stutters in the game. They are off unless you turn them on by hand with `capture.mipmaps = true`.

**Which value wins.** If your file sets `capture.mipmaps` or `capture.max_fps`, that value wins over the profile written in the same file. The `--profile` option on the command line is the exception: it applies the whole profile over the file, including those two values.

Example, in the file:

```toml
profile = "performance"
```

## 🧾 Options

Quick reference. Every option is explained in detail right below the table.

| Option | Default | Accepted values |
|---|---|---|
| `profile` | `"smooth"` | `performance`, `smooth` |
| `screen.monitor` | `"auto"` | `auto`, a number, or part of a monitor name |
| `screen.distance_m` | `2.0` | 0.8 to 6.0 |
| `screen.width_m` | `2.6` | 0.3 to 20.0 |
| `screen.background` | `"auto"` | `auto`, `passthrough`, `black` |
| `capture.backend` | `"auto"` | `auto`, `gpu`, `direct`, `dxcam` |
| `capture.mipmaps` | `false` | `true`, `false` |
| `capture.max_fps` | from the profile | whole number from 0 to 1000 |
| `gyro.hand` | `"right"` | `left`, `right` |
| `gyro.scale` | `1.0` | 0 to 20 |
| `gyro.deadzone_dps` | `1.5` | 0 to 90 |
| `gyro.keepalive` | `true` | `true`, `false` |
| `recenter.hold_s` | `1.0` | 0.2 to 10 |

In the file, the part before the dot is the title of the group and the part after it is the line. For example, `gyro.scale` is written like this:

```toml
[gyro]
scale = 1.5
```

### The screen

**`screen.monitor`: which monitor appears in the headset.** The app shows one Windows monitor on the big screen. With `auto`, it picks the virtual monitor that Virtual Desktop creates (an extra monitor that exists only in software, made for the headset). Without one, it picks a monitor that is not the main one, and as a last option the main monitor. Change it when the wrong monitor appears in the headset. Run `vr-gyro-screen monitors` to see the list: you can use the number shown before a monitor, or part of its name. Example: `monitor = "1"`.

**`screen.distance_m`: how far the screen is, in metres.** It is the starting distance between you and the screen. After you adjust the distance inside the headset (hold Y and move the right stick sideways), the app saves it and the saved value wins over this option, because it is what you chose last.

In the settings window you do not need to think about this: the distance field shows the last adjustment and what you leave there is what is used. From the command line, to go back to the value in the file, delete `screen.json` or start the app with `--distance`. Example: `distance_m = 2.5`.

**`screen.width_m`: how wide the screen is, in metres.** The height follows the shape of the monitor, so a 16:9 monitor stays 16:9. A wider screen at the same distance fills more of your view, like sitting closer to a TV. Change it if the image feels too small to read or too big to take in at once. Example: `width_m = 3.2`.

**`screen.background`: what you see around the screen.** `black` puts the screen in a dark empty space. `passthrough` shows your room through the headset cameras. `auto` shows the room when possible and black otherwise. The room only appears if the runtime (the software on the PC that connects the app to the headset, here the one from Virtual Desktop) lets apps show it. When it does not, the background stays black. Example: `background = "black"`.

### The capture

**`capture.backend`: how the monitor image is copied.** It only changes how much processor the app uses; the image in the headset is the same. Leave it on `auto` unless the troubleshooting page tells you otherwise. The options are compared in [Capture backends](#capture-backends) below. Example: `backend = "direct"`.

**`capture.mipmaps`: smooth shrinking of the image.** Turned on, very fine detail (small text, grass) stays more stable when you move your head, but the graphics card works in short bursts that can show up as stutters in the game. It is off in every profile; turn it on only if fine detail shimmers and the game has power to spare. Example: `mipmaps = true`.

**`capture.max_fps`: the most new images per second.** It limits how many times per second the app copies a new image of the monitor. `0` copies one for every frame the headset shows, which is the smoothest. A lower number saves processor time, and fast motion looks a little less fluid when the game runs faster than the limit. Normally the profile decides. Example: `max_fps = 72`.

### The motion aim

These options change the gyroscope, the motion sensor of the virtual gamepad that the game reads for aiming. The aim only works in games that offer motion (gyro) aiming and recognize a DualShock 4 controller.

**`gyro.hand`: which hand aims.** The motion of this controller becomes the gamepad gyroscope. Change it if you aim with your left hand. Example: `hand = "left"`.

**`gyro.scale`: aim sensitivity inside the app.** The rotation speed of your hand is multiplied by this number before it reaches the game. At `2.0`, a small turn of the wrist moves the aim twice as far; at `0.5`, half as far. Adjust the sensitivity in the game first, because the game's own setting is usually finer. Use this option only when the game's setting is not enough. Example: `scale = 1.5`.

**`gyro.deadzone_dps`: dead zone, to keep the aim still.** A dead zone is a small range of movement that is ignored on purpose. Even a hand at rest shakes a little, and the headset tracking adds tiny noise. When your hand turns slower than this value, in degrees per second, the app sends "no movement", so the aim does not tremble.

Raise it if the aim trembles or creeps while your hand is still. Lower it if very slow, precise aiming feels sticky or ignored, because movements slower than the limit are dropped. The limit applies before `gyro.scale`. Example: `deadzone_dps = 3.0`.

**`gyro.keepalive`: keeps the motion sensor "alive" for the game.** Some games restart their motion sensor when the gyroscope reports exactly the same value for a while, which happens when your hand is still. When this option is on, the app adds a tiny back and forth to the gyroscope on every report, so the value is never exactly the same twice. The movement is far too small to see and averages out to zero, so the aim stays where it is. Leave it on. Turn it off only to check whether a specific game behaves differently without it.

Technical detail: the change is one raw unit of the sensor (1/16 of a degree per second), with the sign alternating on every report. Example: `keepalive = false`.

### Recentering

**`recenter.hold_s`: how long to hold both stick clicks.** Pressing both sticks down (clicking them) and holding brings the screen in front of where you are looking. This option is how many seconds you have to hold before it happens. Raise it if you recenter by accident during play; lower it if the wait bothers you. In the file it goes under `[recenter]`. Example: `hold_s = 1.5`.

### Capture backends

A backend is the method used to copy the image of the monitor. The three give the same image (this was checked pixel by pixel); what changes is the processor work.

| Backend | How it works | Processor use measured on a 1080p monitor at 90 copies per second |
|---|---|---|
| `gpu` | The image stays on the graphics card the whole time. Needs a texture sharing feature from the graphics driver (`WGL_NV_DX_interop2`) | About 7% of one core |
| `direct` | The image passes once through the computer memory for every new image | About 16% of one core |
| `dxcam` | Uses the external `dxcam` library, which keeps a background task and makes several copies per image. Needs an extra install: `pip install ".[dxcam]"` | About 47% of one core |

With `auto`, the app tries `gpu`. If the graphics driver does not offer texture sharing, it uses `direct` and prints a line saying so. `dxcam` is only used when you ask for it by name.

> [!NOTE]
> These numbers come from `vr-gyro-screen bench` on a 1080p monitor. The capture at 1440p and 90 Hz inside the headset was **not measured yet**. Run `vr-gyro-screen bench` on your computer to compare the backends there.

## 🎮 Button mapping

The button mapping says which controller button becomes which gamepad button. When the file is loaded, the app checks every name; a wrong name stops it with a message that lists what is wrong.

**Controller inputs** (the names of the headset controller buttons):

| Name | Button |
|---|---|
| `a`, `b` | A and B, on the right controller |
| `x`, `y` | X and Y, on the left controller |
| `menu` | The menu button, on the left controller |
| `left_stick_click`, `right_stick_click` | Pressing a stick down, like a button |
| `left_trigger`, `right_trigger` | The triggers, under the index finger |
| `left_squeeze`, `right_squeeze` | The grips, on the side of each controller, under the middle finger |

**Gamepad buttons** (the names of the virtual DualShock 4 buttons):

| Name | Button |
|---|---|
| `CROSS`, `CIRCLE`, `SQUARE`, `TRIANGLE` | The four face buttons: bottom, right, left and top |
| `SHOULDER_LEFT`, `SHOULDER_RIGHT` | The left and right shoulder buttons (above the triggers) |
| `THUMB_LEFT`, `THUMB_RIGHT` | Pressing the left or right stick down |
| `OPTIONS`, `SHARE` | The small buttons on the right and on the left of the touchpad |
| `PS` | The round logo button in the middle |
| `TOUCHPAD` | A click on the touchpad |

### `[buttons]`

Each line turns a controller button into a gamepad button. The defaults follow the position of the buttons, so the button at the bottom stays at the bottom:

| Input | Button |
|---|---|
| `a` | `CROSS` |
| `b` | `CIRCLE` |
| `x` | `SQUARE` |
| `left_squeeze` | `SHOULDER_LEFT` |
| `right_squeeze` | `SHOULDER_RIGHT` |
| `left_stick_click` | `THUMB_LEFT` |
| `right_stick_click` | `THUMB_RIGHT` |
| `menu` | `OPTIONS` |

`y` is not in the table because it is the combination key (see `[combo]` below). Important: if you write a `[buttons]` group in your file, it replaces this whole table, not just the lines you wrote. List every button you want, including the ones you keep the same.

### `[triggers]`

| Option | Default | What it does |
|---|---|---|
| `left` | `"left_trigger"` | Which controller input drives the left gamepad trigger |
| `right` | `"right_trigger"` | Which controller input drives the right gamepad trigger |

The gamepad triggers are analog: the game knows how far you pressed, not only whether you pressed. That is why only analog inputs are accepted here: `left_trigger`, `right_trigger`, `left_squeeze` or `right_squeeze`. Example: `left = "left_squeeze"` makes the left grip work as the left trigger.

Two thresholds are fixed. Besides how far it is pressed, the gamepad also reports each trigger as a pressed button, for games that only check that; this happens after 30% of the travel. A grip or trigger used as a plain button in `[buttons]` counts as pressed after 50% of its travel.

### `[combo]`

The headset controllers have fewer buttons than a gamepad. To reach the missing ones, one button works as a combination key, like the Shift key on a keyboard: held together with another button or a stick, it gives something else. By default the key is Y.

| Option | Default | What it does |
|---|---|---|
| `key` | `"y"` | Which button is the combination key. `"none"` turns combinations off. The key cannot also appear in `[buttons]` or `[combo.with]` |
| `solo` | `"TRIANGLE"` | What the key gives when you press it alone. `"none"` for nothing |
| `solo_delay_s` | `0.25` | How long, in seconds, the app waits to decide whether you are pressing the key alone. Range 0 to 5 |
| `dpad` | `true` | Key + left stick gives the directional pad (the four arrow buttons) |
| `screen_adjust` | `true` | Key + right stick moves the screen inside the headset (up and down, nearer and farther). This never reaches the game |
| `with` | `{ x = "SHARE" }` | Key + another button gives a gamepad button. Written as its own group, `[combo.with]` |

**How the key alone works.** When you press Y, the app cannot know yet whether you will combine it with something, so it waits. A quick press (shorter than `solo_delay_s`) reaches the game as a short tap when you let go. If you hold it longer without combining, the solo button stays pressed for as long as you hold.

In practice: lower `solo_delay_s` if TRIANGLE feels late when you hold Y; raise it if TRIANGLE fires by accident when you start a combination slowly. At `0`, TRIANGLE is pressed at once, but it also reaches the game at the start of every combination.

**Combination with another button.** While the key is held, a button listed in `[combo.with]` gives the button written there instead of its normal one. By default Y + X gives SHARE (and not SQUARE).

**Turning combinations off.** With `key = "none"`, Y no longer works as a combination key, and the directional pad and the screen adjustment through the key stop working too. Y then does nothing until you add it to `[buttons]`, for example `y = "TRIANGLE"`.

Example, to also put the PS button on Y + menu (keep `x = "SHARE"`, because this group also replaces the default as a whole):

```toml
[combo.with]
x = "SHARE"
menu = "PS"
```

## 🧪 Not covered by the file

- The `window` and `bench` commands take their own options on the command line, listed in [usage](usage.md). They are not saved in the file.
- The saved screen position lives in `screen.json`, not in this file (see [Where the file goes](#-where-the-file-goes)).
