#!/usr/bin/env bash
# Print the public cloudflared quick-tunnel URLs for frontend + grafana.
# URLs are fetched from each cloudflared container's metrics /quicktunnel endpoint.
# Re-generated on every container (re)start, so always read live — never hardcode.
set -euo pipefail

# service label -> host metrics port (see docker-compose.yml cloudflared-* ports)
services=("Frontend:2000" "Grafana:2001")

fetch() {
  # poll up to ~30s for the tunnel to register and expose its hostname
  local port="$1" host=""
  for _ in $(seq 1 30); do
    host=$(curl -fs "http://127.0.0.1:${port}/quicktunnel" 2>/dev/null \
            | sed -n 's/.*"hostname":"\([^"]*\)".*/\1/p')
    [ -n "$host" ] && { echo "$host"; return 0; }
    sleep 1
  done
  return 1
}

echo ""
echo "🌐 Cloudflare tunnel URLs:"
for entry in "${services[@]}"; do
  label="${entry%%:*}"; port="${entry##*:}"
  if url=$(fetch "$port"); then
    printf "   %-9s https://%s\n" "$label" "$url"
  else
    printf "   %-9s (not ready — is cloudflared-%s up?)\n" "$label" "$(echo "$label" | tr '[:upper:]' '[:lower:]')"
  fi
done
echo ""
