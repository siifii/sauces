# Python dependencies (Pillow + numpy)

Sauces' helper scripts run as `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/<name>"`, so they use **whichever `python3` is first on PATH**. They need Pillow and numpy and nothing else. Any skill can point here.

## Preflight

```bash
python3 -I -c "import PIL, numpy"
```

Exit 0: ready. A failure (`ModuleNotFoundError`), a script's exit 3 (`Missing dependency: <name>. ...`), or an `ImportError` from an inline `python3 -I -c` Pillow command all mean the same thing. Stop the stage, write nothing more, and give the user the guidance below. Never record a design source as unreadable, or a check as failed, because of a missing module.

## Guidance to give the user

Many systems (Homebrew Python on macOS, Debian/Ubuntu) block `pip install` into the system Python (PEP 668, "externally-managed-environment"). Recommend a dedicated virtual environment first:

```bash
python3 -m venv ~/.sauces-venv
~/.sauces-venv/bin/pip install pillow numpy
export PATH="$HOME/.sauces-venv/bin:$PATH"   # add to ~/.zshrc or ~/.bashrc to keep it
```

Then restart Claude Code from that shell (so it inherits the PATH) and run the command again.

Alternatives:

- Where the system Python allows it: `python3 -m pip install --user pillow numpy`.
- Debian/Ubuntu packages: `sudo apt install python3-pil python3-numpy`.

Do not suggest `--break-system-packages`. Do not install anything yourself unless the user asks you to.
