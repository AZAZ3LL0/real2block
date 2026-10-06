#!/usr/bin/env bash
# External probe for monitoring: /healthz answers ok and the certificate is not about to expire.
#   docker/healthcheck.sh https://<domain>
# Caddy renews 30 days before expiry, so fewer than CERT_MIN_DAYS left means renewal is failing.
set -euo pipefail

url=${1:?usage: healthcheck.sh <https-url>}
min_days=${CERT_MIN_DAYS:-14}
attempts=${ATTEMPTS:-3}
read -r -a curl_opts <<<"${CURL_OPTS:-}"

fail() { echo "FAIL: $*" >&2; exit 1; }

body=""
for ((i = 1; i <= attempts; i++)); do
  # A single slow answer is not an outage; retry before alerting.
  if body=$(curl -fsS --max-time 10 "${curl_opts[@]}" "$url/api/v1/healthz"); then
    break
  fi
  body=""
  sleep 5
done
[[ "$body" == '{"status":"ok"}' ]] || fail "healthz did not answer ok after $attempts attempts"

host=${url#https://}
host=${host%%/*}
port=443
if [[ "$host" == *:* ]]; then
  port=${host##*:}
  host=${host%%:*}
fi
cert=$(openssl s_client -connect "$host:$port" -servername "$host" </dev/null 2>/dev/null || true)
openssl x509 -noout -checkend $((min_days * 86400)) <<<"$cert" >/dev/null 2>&1 ||
  fail "certificate of $host is missing or expires in less than $min_days days"

echo "OK: $url"
