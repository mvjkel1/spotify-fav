#!/bin/bash

function show_help() {
    cat << EOF
Usage:
  ./run.sh server      - Run the API server
  ./run.sh tests       - Run all pytest test cases
  ./run.sh help        - Show this help message
EOF
}

function run_server() {
    echo "Starting API server..."
    if uvicorn app.main:app --reload; then
        echo "API server started successfully."
    else
        echo "Error: Failed to start the API server." >&2
        exit 1
    fi
}

function run_tests() {
    echo "Running tests..."
    if pytest -svv; then
        echo "All tests passed successfully."
    else
        echo "Error: Some tests failed." >&2
        exit 1
    fi
}

function main() {
    case $1 in
        server)
            run_server
            ;;
        tests)
            run_tests
            ;;
        help)
            show_help
            ;;
        *)
            echo "Error: '$1' is not a supported option." >&2
            show_help
            exit 1
            ;;
    esac
}

if [[ "$#" -ne 1 ]]; then
    echo "Error: Exactly one argument is required." >&2
    show_help
    exit 1
fi

cd "$(dirname "$0")" || { echo "Error: Failed to change directory." >&2; exit 1; }

main "$1"