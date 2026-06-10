# Demo tape for VHS — renders results/demo.gif
#
#   Install VHS once:  https://github.com/charmbracelet/vhs
#     go install github.com/charmbracelet/vhs@latest   # needs ffmpeg + ttyd
#     # or: brew install vhs   /   apt: see the VHS README
#   Render:            make tape        (or: vhs demo.tape)
#
# Records the live agent trace: schema inspection -> a SQL error -> self-repair
# -> final answer, all from the keyless mock backend (no API key needed).

Output results/demo.gif

Require make

Set Shell bash
Set FontSize 15
Set Width 1320
Set Height 900
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

Type "make demo"
Sleep 600ms
Enter

# Give the trace time to render before the GIF loops.
Sleep 7s
