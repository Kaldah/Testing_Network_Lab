#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/.venv/bin/python" -m main "$@"
