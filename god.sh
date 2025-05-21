#!/bin/sh

set -oue pipefail

let_there_be_light() {
    #
    local -r USER="adelynnmckay"
    local -r REPO="god.sh"
    #
    local -r URL="https://github.com/$USER/$REPO"
    local -r ROOT="${HOME}/.local/share/$REPO"
    #
    local -r DEBUG="${DEBUG:-false}"
    local -r BRANCH="${BRANCH:-main}"
    #
    if [[ -d "$ROOT" ]]; then
        cd "$ROOT"
    else
        git clone "$URL" "$REPO"
    fi
    #
    git fetch --all
    #
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
        git checkout "$BRANCH"
    fi
    #
    git fetch --all
    git reset --hard "origin/$BRANCH"
    #
    cd src
    make
}

help() {
    echo "

    In the beginning, God created the
    heaven and the earth...

    Usage:

        god.sh let-there-be-light"
    "
    exit 1
}

main() {
    case "${1:-}" in
        'let-there-be-light')
            let_there_be_light
        ;;
        *)
            help
        ;;
    esac
}

main ${@:-}