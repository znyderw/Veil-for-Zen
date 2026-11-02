#!/usr/bin/env bash
# Install a source tree into a dedicated virtual environment, without sudo.
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
veil_data="${XDG_DATA_HOME:-$HOME/.local/share}"
veil_bin="$HOME/.local/bin"
veil_env="$veil_data/veil-for-zen/runtime"
case "$veil_data" in /*) ;; *) echo 'XDG_DATA_HOME must be absolute.' >&2; exit 1;; esac
if [[ -L "$veil_env" || ( -d "$veil_env" && ! -f "$veil_env/.veil-managed" ) ]]; then
  echo 'An unrecognized runtime exists. Preserved; installation stopped.' >&2; exit 1
fi
if [[ -e "$veil_bin/veil-for-zen" || -L "$veil_bin/veil-for-zen" ]]; then
  if [[ ! -L "$veil_bin/veil-for-zen" || "$(readlink "$veil_bin/veil-for-zen")" != "$veil_env/bin/veil-for-zen" ]]; then
    echo 'An unrelated veil-for-zen command exists. Preserved; installation stopped.' >&2; exit 1
  fi
fi
if [[ -L "$veil_data/applications/veil-for-zen.desktop" || -L "$veil_data/icons/hicolor/scalable/apps/veil-for-zen.svg" ]]; then
  echo 'Desktop/icon destination is a symlink. Preserved; installation stopped.' >&2; exit 1
fi
if [[ -f "$veil_data/icons/hicolor/scalable/apps/veil-for-zen.svg" && ! -f "$veil_env/.veil-managed" ]] && ! cmp -s "$source_dir/veil_for_zen/assets/veil-for-zen.svg" "$veil_data/icons/hicolor/scalable/apps/veil-for-zen.svg"; then
  echo 'An unrelated icon exists. Preserved; installation stopped.' >&2; exit 1
fi
if [[ -e "$veil_data/applications/veil-for-zen.desktop" ]] && ! grep -q '^X-Veil-Managed=true$' "$veil_data/applications/veil-for-zen.desktop"; then
  echo 'An unrelated desktop entry exists. Preserved; installation stopped.' >&2; exit 1
fi
python3 -m venv "$veil_env"
touch "$veil_env/.veil-managed"
"$veil_env/bin/python" -m pip install "$source_dir"
mkdir -p "$veil_bin" "$veil_data/applications" "$veil_data/icons/hicolor/scalable/apps"
# Symlink avoids shell quoting problems in usernames/paths containing spaces.
if [[ -e "$veil_bin/veil-for-zen" && ! -L "$veil_bin/veil-for-zen" ]]; then
  echo 'An unrelated veil-for-zen command exists. Preserved; installation stopped.' >&2; exit 1
fi
ln -sfn "$veil_env/bin/veil-for-zen" "$veil_bin/veil-for-zen"
"$veil_env/bin/python" - "$source_dir" "$veil_env" "$veil_data" <<'PYCODE'
import sys
from pathlib import Path
source, runtime, data = map(Path, sys.argv[1:])
# Desktop Entry string quoting is not shell quoting.
command=str(runtime/'bin/veil-for-zen').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
text=(source/'packaging/veil-for-zen.desktop').read_text().replace('Exec=veil-for-zen','Exec="'+command+'"')
(data/'applications/veil-for-zen.desktop').write_text(text)
PYCODE
install -m644 "$source_dir/veil_for_zen/assets/veil-for-zen.svg" "$veil_data/icons/hicolor/scalable/apps/veil-for-zen.svg"
echo "Installed. Open Veil for Zen in your application menu, or run $veil_bin/veil-for-zen"
