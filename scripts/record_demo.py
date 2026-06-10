#!/usr/bin/env python3
"""Record a command's terminal output to an asciicast v2 file (stdlib only).

A dependency-light, root-free alternative to ttyd-based recorders: it runs the
command in a pseudo-terminal, timestamps the output, and writes a .cast that
`agg` (https://github.com/asciinema/agg) turns into a GIF. Used by `make gif`.

    python scripts/record_demo.py results/demo.cast make demo
"""
from __future__ import annotations

import json
import os
import pty
import select
import sys
import time

COLS, ROWS = 140, 39


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: record_demo.py <out.cast> <command> [args...]", file=sys.stderr)
        return 2
    out_path, cmd = sys.argv[1], sys.argv[2:]

    events: list[list] = []
    start: float | None = None

    pid, master = pty.fork()
    if pid == 0:  # child
        # rich/shutil.get_terminal_size honor COLUMNS/LINES over the ioctl size,
        # so the trace renders at our chosen width regardless of the real tty.
        os.environ["TERM"] = "xterm-256color"
        os.environ["COLUMNS"] = str(COLS)
        os.environ["LINES"] = str(ROWS)
        os.execvp(cmd[0], cmd)
        os._exit(127)  # unreachable

    # parent: pump the pty until the child exits
    while True:
        try:
            r, _, _ = select.select([master], [], [], 0.1)
        except OSError:
            break
        if master in r:
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            if not data:
                break
            now = time.time()
            if start is None:
                start = now
            events.append([round(now - start, 4), "o", data.decode("utf-8", "replace")])
        else:
            done, _ = os.waitpid(pid, os.WNOHANG)
            if done != 0:
                break

    os.close(master)
    header = {"version": 2, "width": COLS, "height": ROWS,
              "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"}}
    with open(out_path, "w") as f:
        f.write(json.dumps(header) + "\n")
        for e in events:
            f.write(json.dumps(e) + "\n")
    print(f"Wrote {out_path} ({len(events)} chunks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
