#!/bin/bash

function show_help() {
    cat << EOF
Usage:
  ./run.sh server            - Run the API server
  ./run.sh tests             - Run all pytest test cases
  ./run.sh coverage          - Run tests with coverage
  ./run.sh coverage_report   - Run tests with coverage and generate a report
  ./run.sh coverage_html     - Run tests with coverage and generate an HTML report
  ./run.sh help              - Show this help message
EOF
}

function run_server() {
    echo "Starting API server..."
    uvicorn app.main:app --reload
}

function run_tests() {
    echo "Running tests..."
    pytest -svv
}

function run_coverage() {
    echo "Running tests with coverage..."
    coverage run -m pytest

    case $1 in
        report)
            echo "Generating coverage report..."
            coverage report -m
            ;;
        html)
            echo "Generating HTML coverage report..."
            coverage html
            ;;
    esac
}

function main() {
    case $1 in
        server)
            run_server
            ;;
        tests)
            run_tests
            ;;
        coverage)
            run_coverage
            ;;
        coverage_report)
            run_coverage report
            ;;
        coverage_html)
            run_coverage html
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