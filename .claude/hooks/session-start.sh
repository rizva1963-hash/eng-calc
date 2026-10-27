#!/bin/bash
# Installs CLI tools for cloud sessions: yt-dlp (watch plugin), markitdown (PDF/Office -> Markdown), graphify (code knowledge graph).
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
export PATH="$HOME/.local/bin:$PATH"
command -v yt-dlp >/dev/null 2>&1 || pip install -q yt-dlp
command -v markitdown >/dev/null 2>&1 || pip install -q 'markitdown[pdf,docx,xlsx,pptx]'
command -v graphify >/dev/null 2>&1 || { uv tool install -q graphifyy && graphify install --platform claude >/dev/null; }
