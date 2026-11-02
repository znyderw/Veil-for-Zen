#!/usr/bin/env bash
set -euo pipefail
veil_data="${XDG_DATA_HOME:-$HOME/.local/share}"
veil_env="$veil_data/veil-for-zen/runtime"
case "$veil_data" in /*) ;; *) echo 'XDG_DATA_HOME must be absolute.' >&2; exit 1;; esac
# Remove only the runtime and our own entry points. Preserve user data and profiles.
if [[ -L "$HOME/.local/bin/veil-for-zen" && "$(readlink "$HOME/.local/bin/veil-for-zen")" == "$veil_env/bin/veil-for-zen" ]]; then
  rm -- "$HOME/.local/bin/veil-for-zen"
fi
if [[ -f "$veil_data/applications/veil-for-zen.desktop" ]] && grep -q '^X-Veil-Managed=true$' "$veil_data/applications/veil-for-zen.desktop"; then
  rm -- "$veil_data/applications/veil-for-zen.desktop"
fi
veil_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if cmp -s "$veil_source/veil_for_zen/assets/veil-for-zen.svg" "$veil_data/icons/hicolor/scalable/apps/veil-for-zen.svg"; then
  rm -- "$veil_data/icons/hicolor/scalable/apps/veil-for-zen.svg"
fi
if [[ -f "$veil_env/pyvenv.cfg" && -f "$veil_env/.veil-managed" && ! -L "$veil_env" ]]; then rm -rf -- "$veil_env"; fi
echo 'Veil removed. User settings, images, presets, backups and Zen profiles were preserved.'
