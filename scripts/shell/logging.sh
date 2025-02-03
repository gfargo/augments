#!/bin/bash

# ANSI color and style codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
ITALIC='\033[3m'
UNDERLINE='\033[4m'
NC='\033[0m' # No Color

# Unicode symbols
CHECK_MARK="✓"
CROSS_MARK="✗"
WARNING_MARK="⚠"
INFO_MARK="ℹ"
ARROW_MARK="➜"
BULLET_MARK="•"
GEAR_MARK="⚙"
CLOCK_MARK="⏱"

# Logging functions
log_header() {
    local title="$1"
    local width=50
    local padding=$(( (width - ${#title}) / 2 ))
    printf "\n${BLUE}${BOLD}%${padding}s%s%${padding}s${NC}\n" "" "$title" ""
    printf "${BLUE}${BOLD}%${width}s${NC}\n" | tr ' ' '='
}

log_subheader() {
    printf "\n${MAGENTA}${BOLD}▶ %s${NC}\n" "$1"
}

log_info() {
    printf "${CYAN}${INFO_MARK} %s${NC}\n" "$1"
}

log_success() {
    printf "${GREEN}${CHECK_MARK} %s${NC}\n" "$1"
}

log_warning() {
    printf "${YELLOW}${WARNING_MARK} %s${NC}\n" "$1" >&2
}

log_error() {
    printf "${RED}${CROSS_MARK} %s${NC}\n" "$1" >&2
}

log_debug() {
    if [ "${DEBUG:-0}" = "1" ]; then
        printf "${GRAY}${GEAR_MARK} %s${NC}\n" "$1" >&2
    fi
}

log_step() {
    local current="$1"
    local total="$2"
    local description="$3"
    local prefix="${MAGENTA}${BOLD}[${current}/${total}]${NC}"
    local bullet="${WHITE}${BULLET_MARK}${NC}"
    printf "%s %s %s\n" "$prefix" "$bullet" "$description"
}

log_command() {
    printf "${GRAY}${ARROW_MARK} ${ITALIC}%s${NC}\n" "$1"
}

log_detail() {
    printf "  ${DIM}${BULLET_MARK} %s${NC}\n" "$1"
}

log_timing() {
    printf "${CYAN}${CLOCK_MARK} %s${NC}\n" "$1"
}

# Progress bar function
show_progress() {
    local current=$1
    local total=$2
    local width=40
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r${BLUE}${BOLD}Progress: ${NC}"
    printf "["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] ${percentage}%%"
}

# Spinner function with message
show_spinner() {
    local pid=$1
    local message=$2
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    
    while kill -0 $pid 2>/dev/null; do
        i=$(( (i + 1) % ${#spin} ))
        printf "\r${CYAN}${spin:$i:1}${NC} %s" "$message"
        sleep 0.1
    done
    printf "\r"
}

# Timer function
start_timer() {
    timer_start=$(date +%s)
}

end_timer() {
    local timer_end=$(date +%s)
    local duration=$((timer_end - timer_start))
    log_timing "Operation took ${duration}s"
}

# Section functions
start_section() {
    log_subheader "$1"
    start_timer
}

end_section() {
    end_timer
    echo
}

# Status line function
status_line() {
    local status="$1"
    local message="$2"
    case "$status" in
        "ok") printf "${GREEN}${CHECK_MARK}${NC} %s\n" "$message" ;;
        "error") printf "${RED}${CROSS_MARK}${NC} %s\n" "$message" ;;
        "warning") printf "${YELLOW}${WARNING_MARK}${NC} %s\n" "$message" ;;
        "info") printf "${BLUE}${INFO_MARK}${NC} %s\n" "$message" ;;
    esac
}

# Example usage:
# log_header "Starting Installation"
# 
# start_section "Checking Prerequisites"
# log_command "checking python3..."
# status_line "ok" "Python 3.8.5 found"
# log_command "checking pip..."
# status_line "warning" "Pip needs update"
# end_section
# 
# start_section "Installing Dependencies"
# for i in {1..10}; do
#     show_progress $i 10
#     sleep 0.2
# done
# echo
# end_section
# 
# log_success "Installation Complete"

# Function to show spinner while a command runs
show_spinner() {
    local -r pid="$1"
    local -r delay='0.1'
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local temp
    local message="$2"
    
    printf "${CYAN}"
    while ps a | awk '{print $1}' | grep -q "$pid"; do
        temp="${spinstr#?}"
        printf "\r%s %s" "${spinstr:0:1}" "$message"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
    done
    printf "\r${NC}"
}

# Function to run a command with a spinner
run_with_spinner() {
    local message="$1"
    shift
    printf "${CYAN}%s...${NC}" "$message"
    ("$@") &> /dev/null &
    show_spinner $! "$message"
    local exit_code=$?
    echo
    return $exit_code
}

# Function to time a command
time_command() {
    local start=$(date +%s)
    "$@"
    local exit_code=$?
    local end=$(date +%s)
    local duration=$((end - start))
    log_debug "Command took ${duration}s to complete"
    return $exit_code
}

# Example usage:
# source scripts/shell/logging.sh
#
# log_header "Starting Installation"
# log_info "Checking dependencies..."
# log_success "Dependencies installed"
# log_warning "Config file not found, using defaults"
# log_error "Failed to connect to server"
# log_debug "Debug message"
# log_step 1 3 "Installing packages"
#
# run_with_spinner "Installing dependencies" sleep 2
# time_command some_long_running_command