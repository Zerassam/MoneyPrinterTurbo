#!/bin/sh
set -eu
PORT="${PORT:-8501}"
exec streamlit run ./webui/Main.py \
  --server.address=0.0.0.0 \
  --server.port="$PORT" \
  --browser.serverAddress=0.0.0.0 \
  --server.enableCORS=True \
  --browser.gatherUsageStats=False \
  --client.toolbarMode=minimal \
  --logger.hideWelcomeMessage=True \
  --server.showEmailPrompt=False
