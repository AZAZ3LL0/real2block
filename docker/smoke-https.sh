#!/usr/bin/env bash
# Checks a running HTTPS stack: redirect, TLS, HSTS and the security headers of tech.md §8.2.
#   docker/smoke-https.sh <host> [http_port] [https_port]
# Extra curl flags go in CURL_OPTS, e.g. CURL_OPTS=-k for Caddy's internal CA on localhost.
set -euo pipefail

host=${1:?usage: smoke-https.sh <host> [http_port] [https_port]}
http_port=${2:-80}
https_port=${3:-443}
base="https://$host:$https_port"
read -r -a curl_opts <<<"${CURL_OPTS:-}"

fail() { echo "FAIL: $*" >&2; exit 1; }

headers() {
  curl -sS -D - -o /dev/null "${curl_opts[@]}" "$@" | tr -d '\r'
}

header_values() {
  grep -i "^$2:" <<<"$1" | cut -d: -f2- | sed 's/^ //' || true
}

redirect=$(headers "http://$host:$http_port/")
grep -qE '^HTTP/[0-9.]+ 30[18]' <<<"$redirect" || fail "plain HTTP is not redirected"
grep -qi '^location: https://' <<<"$redirect" || fail "redirect does not point to https"

required=(
  "Strict-Transport-Security: max-age=31536000; includeSubDomains"
  "Content-Security-Policy: default-src 'self'; img-src 'self' blob: data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
  "X-Content-Type-Options: nosniff"
  "Referrer-Policy: no-referrer"
  "X-Frame-Options: DENY"
  "Permissions-Policy: camera=(), microphone=(), geolocation=()"
)

for path in / /api/v1/healthz; do
  response=$(headers "$base$path")
  grep -qE '^HTTP/[0-9.]+ 200' <<<"$response" || fail "$path is not 200 over HTTPS"
  for line in "${required[@]}"; do
    name=${line%%:*}
    values=$(header_values "$response" "$name")
    # One copy only: Caddy must replace, not duplicate, what the API already sets.
    [[ "$values" == "${line#*: }" ]] || fail "$path: $name is '${values//$'\n'/ | }'"
  done
  [[ -z $(header_values "$response" Server) ]] || fail "$path leaks the Server header"
done

echo "OK: $base"
