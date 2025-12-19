#!/bin/bash

# wait_until_idle.sh
# Waits until CPU usage is below a threshold for a specified duration

# Default values
THRESHOLD=100
DURATION=30
CHECK_INTERVAL=1

# Show usage
show_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Waits until CPU usage is below a threshold for a specified duration.

OPTIONS:
    -t, --threshold PERCENT    CPU usage threshold (default: 100)
    -d, --duration SECONDS     Duration in seconds to remain below threshold (default: 30)
    -h, --help                 Show this help message

EXAMPLES:
    $(basename "$0")                    # Wait until CPU < 100% for 30 seconds
    $(basename "$0") -t 50 -d 60        # Wait until CPU < 50% for 60 seconds
    $(basename "$0") --threshold 25     # Wait until CPU < 25% for 30 seconds

EOF
    exit 0
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--threshold)
            THRESHOLD="$2"
            if ! [[ "$THRESHOLD" =~ ^[0-9]+$ ]] || [ "$THRESHOLD" -lt 0 ] || [ "$THRESHOLD" -gt 100 ]; then
                echo "Error: Threshold must be a number between 0 and 100" >&2
                exit 1
            fi
            shift 2
            ;;
        -d|--duration)
            DURATION="$2"
            if ! [[ "$DURATION" =~ ^[0-9]+$ ]] || [ "$DURATION" -lt 1 ]; then
                echo "Error: Duration must be a positive number" >&2
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            echo "Use -h or --help for usage information" >&2
            exit 1
            ;;
    esac
done

echo "Waiting until CPU usage is below ${THRESHOLD}% for ${DURATION} consecutive seconds..."

idle_seconds=0

while true; do
    # Get CPU idle percentage and calculate usage
    # On macOS, using top command with one sample
    cpu_idle=$(top -l 1 | grep "CPU usage" | awk '{print $7}' | sed 's/%//')

    # Calculate CPU usage (100 - idle)
    cpu_usage=$(echo "100 - $cpu_idle" | bc)

    # Compare with threshold
    if (( $(echo "$cpu_usage < $THRESHOLD" | bc -l) )); then
        idle_seconds=$((idle_seconds + CHECK_INTERVAL))
        echo "CPU usage: ${cpu_usage}% (idle for ${idle_seconds}/${DURATION}s)"

        if [ $idle_seconds -ge $DURATION ]; then
            echo "CPU has been below ${THRESHOLD}% for ${DURATION} seconds. Continuing..."
            exit 0
        fi
    else
        if [ $idle_seconds -gt 0 ]; then
            echo "CPU usage: ${cpu_usage}% (reset counter)"
        else
            echo "CPU usage: ${cpu_usage}% (waiting...)"
        fi
        idle_seconds=0
    fi

    sleep $CHECK_INTERVAL
done
