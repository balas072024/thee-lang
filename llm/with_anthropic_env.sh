#!/usr/bin/env bash
# Run a command with ANTHROPIC_API_KEY / ANTHROPIC_WORKSPACE_ID taken from an existing .env file,
# without printing them.   bash llm/with_anthropic_env.sh ~/Claude/manbalai/backend/.env python3 ...
set -euo pipefail
ENV_FILE=$1; shift
while IFS= read -r line; do
  case "$line" in
    ANTHROPIC_API_KEY=*|ANTHROPIC_WORKSPACE_ID=*)
      name=${line%%=*}; value=${line#*=}; value=${value%\"}; value=${value#\"}; value=${value%\'}; value=${value#\'}
      export "$name=$value" ;;
  esac
done < "$ENV_FILE"
[ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "No ANTHROPIC_API_KEY in $ENV_FILE" >&2; exit 1; }
exec "$@"
