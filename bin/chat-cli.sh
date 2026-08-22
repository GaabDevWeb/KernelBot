#!/usr/bin/env bash
# Chat CLI contra o Kernel API (POST /chat JSON).
# Uso:
#   ./bin/chat-cli.sh
#   ./bin/chat-cli.sh "O que é normalização SQL?"
#   KERNEL_BASE_URL=http://127.0.0.1:8001 ./bin/chat-cli.sh
set -euo pipefail

BASE_URL="${KERNEL_BASE_URL:-http://127.0.0.1:8001}"
CHANNEL="${KERNEL_CHANNEL:-cli}"
USER_ID="${KERNEL_USER_ID:-terminal}"
DISCIPLINE="${KERNEL_DISCIPLINE:-}"
SESSION_ID="${KERNEL_SESSION_ID:-cli_$(date +%s)}"
HISTORY_FILE="${KERNEL_HISTORY_FILE:-/tmp/kernelbot-cli-history-${SESSION_ID}.json}"

if ! command -v curl >/dev/null 2>&1; then
  echo "ERRO: curl é obrigatório"
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "ERRO: jq é obrigatório (sudo apt install jq)"
  exit 1
fi

if ! curl -fsS --max-time 3 "${BASE_URL}/health" >/dev/null; then
  echo "ERRO: Kernel não responde em ${BASE_URL}/health"
  echo "      Arranque antes: ./bin/staging-serve.sh   ou   .venv/bin/python main.py"
  exit 1
fi

echo "[]" >"${HISTORY_FILE}"
echo "Kernel CLI  →  ${BASE_URL}"
echo "session_id  →  ${SESSION_ID}"
echo "Comandos: /sair  |  /limpar  |  /health  |  /search <texto>"
echo ""

ask_once() {
  local message="$1"
  local history
  history="$(cat "${HISTORY_FILE}")"

  local payload
  payload="$(jq -n \
    --arg message "${message}" \
    --arg user_id "${USER_ID}" \
    --arg channel "${CHANNEL}" \
    --arg session_id "${SESSION_ID}" \
    --arg discipline "${DISCIPLINE}" \
    --argjson history "${history}" \
    '{
      user_id: $user_id,
      message: $message,
      channel: $channel,
      session_id: $session_id,
      history: $history,
      stream: false,
      metadata: {}
    } + (if $discipline == "" then {} else {discipline: $discipline} end)')"

  local response
  response="$(curl -fsS -X POST "${BASE_URL}/chat" \
    -H "Content-Type: application/json" \
    -d "${payload}")"

  local answer
  answer="$(echo "${response}" | jq -r '.answer // empty')"
  local discipline_out
  discipline_out="$(echo "${response}" | jq -r '.discipline // "-"')"
  local confidence
  confidence="$(echo "${response}" | jq -r '.confidence // "-"')"
  local sources
  sources="$(echo "${response}" | jq -r '(.sources // []) | join(", ")')"

  echo ""
  echo "── resposta (discipline=${discipline_out} confidence=${confidence}) ──"
  echo "${answer}"
  if [[ -n "${sources}" ]]; then
    echo ""
    echo "fontes: ${sources}"
  fi
  echo "────────────────────────────────────────────────"

  jq -n \
    --argjson history "${history}" \
    --arg user "${message}" \
    --arg assistant "${answer}" \
    '$history + [{role:"user",content:$user},{role:"assistant",content:$assistant}]' \
    >"${HISTORY_FILE}"
}

search_once() {
  local message="$1"
  curl -fsS -X POST "${BASE_URL}/search" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg m "${message}" --arg c "${CHANNEL}" --arg u "${USER_ID}" \
      '{message:$m, channel:$c, user_id:$u, top_k:5}')" \
    | jq .
}

if [[ "${1:-}" != "" ]]; then
  ask_once "$*"
  exit 0
fi

while true; do
  printf "você> "
  # shellcheck disable=SC2162
  read -r line || break
  [[ -z "${line}" ]] && continue
  case "${line}" in
    /sair|/exit|/quit) break ;;
    /limpar|/reset)
      echo "[]" >"${HISTORY_FILE}"
      echo "(histórico limpo)"
      ;;
    /health)
      curl -fsS "${BASE_URL}/health" | jq .
      ;;
    /search\ *)
      search_once "${line#/search }"
      ;;
    *)
      ask_once "${line}"
      ;;
  esac
done

echo "Até logo."
