#!/bin/sh

set -oue

let_there_be_light() {
    echo "hello world"
}

help() {
cat << EOF
    
    In the beginning, God created the 
    heaven and the earth...
    
    Usage: 
        
        god.sh let-there-be-light

EOF
    exit 1
}

main() {
    case "$1" in
    'let-there-be-light')
        let_there_be_light
    ;;
    *)
        help
    ;;
    esac
}

main ${@:-}