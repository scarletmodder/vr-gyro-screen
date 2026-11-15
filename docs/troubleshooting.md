**English** | [Português](troubleshooting.pt-BR.md)

# 🩺 Troubleshooting

Find what is happening to you, see the likely cause, and follow what to do. While it runs, the app prints short status lines in English (in the command line window, when you start it from there). Many entries below start with the exact text of one of those lines, so you can match it. Things that cannot be fixed yet are not in these tables: they are in [Known limitations](#-known-limitations). Back to the [README](../README.md).

## 🎮 Controls and aiming

| What happens | Likely cause | What to do |
|---|---|---|
| The game plays by itself after you put the controllers down | Hand tracking (the headset following your bare hands with its cameras) is on. When you let go of the controllers, the headset switches to your hands, the aim jumps, and a pinch of your fingers counts as a trigger press | Turn hand tracking off in the headset settings |
| The app gets no button presses, or the game sees two controllers | The **Use controllers as gamepad** option is on in the **INPUT** tab of Virtual Desktop. Then Virtual Desktop takes the controllers for itself | Turn that option off |
| The controls stop while the headset menu is open | This is on purpose: while the headset menu is open, the app releases every button and stops the aim, so nothing stays pressed in the game | Close the headset menu and the controls come back |
| Y does not seem to press TRIANGLE | Y is the combination key. Pressed alone, it gives TRIANGLE only when you let go of a quick press, or after 0.25 seconds when you hold it. During those 0.25 seconds the app waits to see whether you are starting a combination | Tap Y and let go, or hold it a moment. To change this, see `combo.solo_delay_s`, `combo.key` and `combo.solo` in the [configuration](configuration.md) |
| Moving the controller does not move the aim in the game | The game only uses the motion sensor when its gyro (motion) aiming is turned on, and only if it recognizes the controller as a DualShock 4 | In the game's controller settings, turn gyro aiming on. Then adjust the sensitivity there, before you change `gyro.scale` |
| The aim trembles or creeps while your hand is still | Small shakes of the hand and of the headset tracking go past the dead zone (the range of small movements the app ignores) | Raise `gyro.deadzone_dps` a little, for example to `3.0`, in the [configuration](configuration.md) |
| Slow, precise aiming feels sticky | Movements slower than the dead zone are ignored | Lower `gyro.deadzone_dps`, for example to `1.0` |
| The aim is too fast or too slow even at the limit of the game's setting | The game's sensitivity range is not enough for you | Change `gyro.scale` (above 1 is faster, below 1 is slower) |

## 🖥️ Screen and image

| What happens | Likely cause | What to do |
|---|---|---|
| The screen is off to the side or too high | The screen stays where you last recentered, and you moved or turned since then | Hold both stick clicks (press both sticks down) for 1 second while you look where you want the screen. See also [Recenter the screen](usage.md) |
| The screen is too near or too far | The distance you adjusted inside the headset was saved, and it wins over `screen.distance_m` | Hold Y and move the right stick to the right (nearer) or to the left (farther). You can also type the distance on the **Screen** page of the window before pressing **Start**. From the command line, start the app with `--distance`, or delete `screen.json` in `%APPDATA%\vr-gyro-screen` |
| Fine detail, such as small text or grass, shimmers | Mipmaps are off by default. They are smaller copies of the image that keep fine detail stable when it is shrunk to fit the headset, but they can make the game stutter | Set `capture.mipmaps = true` in the settings file (see [configuration](configuration.md)), and turn it off again if the game starts to stutter. If it is already on, see "Fine detail shimmers even with mipmaps on" in [Known limitations](#-known-limitations) |
| The background is black instead of your room | `screen.background` is set to `black` | Set it to `auto` or `passthrough`. If the line `background: this runtime does not offer passthrough to apps; using black` appears, see [Known limitations](#-known-limitations) |

## 🔌 Monitor and capture

| What happens | Likely cause | What to do |
|---|---|---|
| `no monitor matches "..."` | The text in `screen.monitor` (or `--monitor`) is not part of the name of any monitor. The line also lists the monitors found | Run `vr-gyro-screen monitors` and use the number of the monitor, or part of its name |
| `there is no monitor N; M found` | The number is higher than the last monitor in the list. The list starts at 0 | Run `vr-gyro-screen monitors` and use a number from that list |
| `Windows reports no monitor attached to the desktop` | Windows has no active monitor at that moment | Check that a monitor is on and connected, then start the app again |
| The wrong monitor appears in the headset | With `auto`, the app looks for the virtual monitor of Virtual Desktop. When it does not exist, the app uses another monitor that is not the main one, and in the end the main one | Check in Virtual Desktop that its virtual monitor is on, then run `vr-gyro-screen monitors` to see which one the app picks. You can also choose it with `screen.monitor` |
| `capture: lost the monitor (...); waiting for it to come back` | Virtual Desktop removes its virtual monitor and creates another one when you change the frame rate or reconnect the headset | Wait a few seconds. When the new monitor appears, the line `capture: the monitor is back` shows up and the image returns. Your game may need a moment on the new monitor |
| `capture: could not reopen the monitor (...); still trying` | The monitor came back, but the app could not set up the image again yet | Wait: the app tries again every second, and the controls keep working meanwhile. If the image never comes back, close the app and start it again |
| `could not capture the monitor: ...` | The capture could not start when the app opened | Run `vr-gyro-screen monitors` to check the monitor, then try starting with `--backend direct` |
| `the dxcam backend needs the optional package` | `capture.backend` (or `--backend`) asks for `dxcam`, and that extra package is not installed | Set the backend back to `auto`, or install the package with `pip install ".[dxcam]"` in the folder of the project |
| `rotated monitors are not supported` | The monitor is set to portrait or upside down in the Windows display settings | Set it to landscape in Windows, or choose another monitor |
| The game does not go full screen on the headset monitor | The game did not receive its full screen key right after its window was moved | Run `vr-gyro-screen window "part of the title"` again. If the game does not use F11 for full screen, add `--fullscreen-key alt+enter`, or `--fullscreen-key none` to only move and maximize the window |
| `Windows did not let the window come to the front, so no key was pressed; click it once` | Windows only sends keys to the window in front, and it refused to bring the game window forward | Click the game window once, then run the `window` command again |
| `no visible window has "..." in its title` | No open window has that text in its title within the waiting time (60 seconds by default) | Check the title of the game window and use part of it. If the game takes long to open, use `--wait` with more seconds |

## ⚙️ Installation and configuration

| What happens | Likely cause | What to do |
|---|---|---|
| `vr-gyro-screen only runs on Windows` | The app was started on another system | Run it on Windows |
| `configuration problem: ... has unknown keys` | A typo in a name, or an option that does not exist | Compare your file with [config.example.toml](../config.example.toml). The message names the group and the wrong names |
| `configuration problem: ... must be between ...` or `... must be one of ...` | A value is out of the accepted range or is not one of the accepted words | Use a value from the [configuration](configuration.md) page |
| `configuration problem: ... is not a gamepad button` or `... is not a controller input` | A button name outside the lists | Use the names listed in [Button mapping](configuration.md) |
| `configuration problem: combo.key ... is also used in [buttons]` (or `[combo.with]`) | The combination key cannot also be a plain button, or it would reach the game in every combination | Remove that button from `[buttons]` or `[combo.with]` |
| `configuration problem: ... is not valid TOML` | The file has a writing mistake, such as missing quotes around a word or a missing bracket | Check the line given in the message. Text values go in quotes (`hand = "left"`), numbers and `true`/`false` do not |
| `configuration problem: configuration file not found` | The file passed with `--config` does not exist at that path | Fix the path. Without `--config`, having no file in the default folder is fine |
| `could not create the virtual gamepad (...)` | The ViGEmBus driver (the Windows driver that creates the virtual gamepad) is missing or not working | Install or repair ViGEmBus, then start the app again |
| `the headset session failed (...)` | The headset is not connected, or the OpenXR runtime is not active. OpenXR is the standard that lets the app talk to the headset; the runtime is the software on the PC that does that work, here the one that comes with Virtual Desktop | Connect the headset through Virtual Desktop and check that the Virtual Desktop OpenXR runtime (VDXR) is the active one, then start the app again |

## 🐢 Performance

Every 10 seconds the app prints a summary line (unless you start it with `--quiet`):

```text
90 frames/s, worst gap 12 ms, 0 late, capture 0.20 ms per frame, session FOCUSED
```

The numbers above only show the shape of the line; yours will differ.

| Part of the line | What it means | What is good |
|---|---|---|
| frames/s | How many images per second the app delivered to the headset | Close to the frame rate of the headset (for example 90) |
| worst gap | The longest time between two images in those 10 seconds. A high value is a stutter you may have felt | Close to one frame (about 11 ms at 90 Hz) |
| late | How many images took one and a half frames or more. Each one is a small stutter | 0, or close to it |
| capture | Average time spent copying the monitor image, per image | As low as possible, since it is part of the time of every frame |
| session | The state of the connection with the headset. The controls only work in `FOCUSED`. Another state appears, for example, while the headset menu is open | `FOCUSED` while you play |

If the game stutters or the processor use is high, change to the `performance` profile (the default is `smooth`) and keep `capture.mipmaps` off (see [Profiles](configuration.md)). `vr-gyro-screen bench` compares the capture backends on your computer, without the headset.

## 🚧 Known limitations

These are things the app does not handle yet. There is no fix on your side, but some of them can be softened.

**The mouse pointer does not appear in the headset.** The capture copies the image of the desktop, and Windows draws the mouse pointer separately, on top of that image. The app does not draw the pointer by itself yet, so it is missing from the screen in the headset. What helps: most games hide the pointer during play and use the gamepad in their menus, so you only notice it on the Windows desktop or in programs that need the mouse.

**The room does not appear around the screen on some runtimes.** The line is `background: this runtime does not offer passthrough to apps; using black`. Passthrough (showing your room through the headset cameras) depends on the runtime letting apps use it. When it does not, the app falls back to a black background by itself and keeps working normally. The app cannot turn this on from its side. To stop seeing the line, set `screen.background` to `auto` or `black`.

**Fine detail shimmers even with mipmaps on.** The line is `the runtime refused N mipmap levels (...); continuing without`. Some runtimes do not accept the image with mipmaps, so the app keeps going without them and the image looks as it does with mipmaps off: fine detail may shimmer. What may help: a larger screen in your view (higher `screen.width_m` or a shorter distance) means the image is shrunk less, so there is less shimmer.

**The capture uses a little more processor on some graphics cards.** The line is `capture: staying on the processor path (...)`. The cheapest capture method needs a texture sharing feature from the graphics driver. When the driver does not offer it, the app uses the `direct` method, which works the same and shows the same image, with a little more processor use (see [Capture backends](configuration.md)). What helps, if the processor is busy: the `performance` profile keeps the capture work low.

## 🧪 Not tested

Only one setup was tested: a Meta Quest headset with Virtual Desktop and its OpenXR runtime was tested. Other headsets, other OpenXR runtimes and other graphics cards were not tested. The capture cost inside the headset at 1440p and 90 Hz was not measured yet. If something fails in a setup like that, you are on new ground, and the lines the app prints are the best starting point to understand what happened.
