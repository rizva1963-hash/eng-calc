#!/bin/bash
# Installs CLI tools for cloud sessions: yt-dlp (watch plugin), markitdown (PDF/Office -> Markdown).
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
command -v yt-dlp >/dev/null 2>&1 || pip install -q yt-dlp
command -v markitdown >/dev/null 2>&1 || pip install -q 'markitdown[pdf,docx,xlsx,pptx]'
