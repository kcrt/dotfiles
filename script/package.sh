#!/bin/bash

# package.sh - Universal package manager wrapper
# Written by kcrt <kcrt@kcrt.net>
# Provides unified interface for package management across different systems

set -e

# Function to detect package manager
detect_package_manager() {
    if command -v brew &> /dev/null; then
        echo "brew"
    elif command -v apt &> /dev/null; then
        echo "apt"
    elif command -v yum &> /dev/null; then
        echo "yum"
    else
        echo "unknown"
    fi
}

# Usage information
show_usage() {
    cat << EOF
Usage: package.sh <command> [package_name]

Commands:
  update              Update package database/repositories
  upgrade [package]   Upgrade specified package or all packages
  install <package>   Install a package
  uninstall <package> Uninstall a package
  search <query>      Search packages containing the query string
  provides <file>     Find package that provides the specified file
  list                List all available packages
  list installed     List all installed packages
  info <package>      Show detailed information about a package
  infoweb <package>   Open package homepage/website in browser

Examples:
  package.sh update
  package.sh install vim
  package.sh search python
  package.sh provides stdio.h
  package.sh list installed
  package.sh info python3
  package.sh infoweb nginx
EOF
}

# Homebrew functions
brew_update() {
    brew update
}

brew_upgrade() {
    if [ $# -eq 0 ]; then
        brew upgrade
    else
        brew upgrade "$1"
    fi
}

brew_install() {
    brew install "$1"
}

brew_uninstall() {
    brew uninstall "$1"
}

brew_search() {
    brew search "$1"
}

brew_provides() {
    echo "Note: Homebrew doesn't have a direct 'provides' command."
    echo "Searching for packages that might contain '$1'..."
    brew search "$1"
}

brew_list() {
    brew search
}

brew_list_installed() {
    brew list
}

brew_info() {
    brew info "$1"
}

brew_infoweb() {
    brew homepage "$1"
}

# APT functions
apt_update() {
    sudo apt update
}

apt_upgrade() {
    if [ $# -eq 0 ]; then
        sudo apt upgrade
    else
        sudo apt upgrade "$1"
    fi
}

apt_install() {
    sudo apt install "$1"
}

apt_uninstall() {
    sudo apt remove "$1"
}

apt_search() {
    apt search "$1"
}

apt_provides() {
    if command -v apt-file &> /dev/null; then
        apt-file search "$1"
    else
        echo "apt-file is not installed. Installing it..."
        sudo apt install apt-file
        sudo apt-file update
        apt-file search "$1"
    fi
}

apt_list() {
    apt list
}

apt_list_installed() {
    apt list --installed
}

apt_info() {
    apt show "$1"
}

apt_infoweb() {
    # apt doesn't have a direct homepage command, but we can try to extract URL from package info
    local info_output
    info_output=$(apt show "$1" 2>/dev/null)
    local homepage
    homepage=$(echo "$info_output" | grep "^Homepage:" | cut -d' ' -f2- | head -n1)
    if [ -n "$homepage" ]; then
        echo "Opening homepage: $homepage"
        if command -v open &> /dev/null; then
            open "$homepage"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$homepage"
        else
            echo "No browser opener found. Homepage: $homepage"
        fi
    else
        echo "No homepage found for package '$1'"
    fi
}

# YUM functions
yum_update() {
    sudo yum update
}

yum_upgrade() {
    if [ $# -eq 0 ]; then
        sudo yum update
    else
        sudo yum update "$1"
    fi
}

yum_install() {
    sudo yum install "$1"
}

yum_uninstall() {
    sudo yum remove "$1"
}

yum_search() {
    yum search "$1"
}

yum_provides() {
    yum provides "$1"
}

yum_list() {
    yum list available
}

yum_list_installed() {
    yum list installed
}

yum_info() {
    yum info "$1"
}

yum_infoweb() {
    # yum doesn't have a direct homepage command, but we can try to extract URL from package info
    local info_output
    info_output=$(yum info "$1" 2>/dev/null)
    local homepage
    homepage=$(echo "$info_output" | grep "^URL" | cut -d':' -f2- | sed 's/^ *//' | head -n1)
    if [ -n "$homepage" ]; then
        echo "Opening homepage: $homepage"
        if command -v open &> /dev/null; then
            open "$homepage"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$homepage"
        else
            echo "No browser opener found. Homepage: $homepage"
        fi
    else
        echo "No homepage found for package '$1'"
    fi
}

# Main script logic
main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi

    PACKAGE_MANAGER=$(detect_package_manager)
    
    if [ "$PACKAGE_MANAGER" = "unknown" ]; then
        echo "Error: No supported package manager found (brew, apt, yum)"
        exit 1
    fi

    COMMAND="$1"
    shift

    case "$COMMAND" in
        update)
            ${PACKAGE_MANAGER}_update "$@"
            ;;
        upgrade)
            ${PACKAGE_MANAGER}_upgrade "$@"
            ;;
        install)
            if [ $# -eq 0 ]; then
                echo "Error: Package name required for install command"
                exit 1
            fi
            ${PACKAGE_MANAGER}_install "$@"
            ;;
        uninstall|remove)
            if [ $# -eq 0 ]; then
                echo "Error: Package name required for uninstall command"
                exit 1
            fi
            ${PACKAGE_MANAGER}_uninstall "$@"
            ;;
        search)
            if [ $# -eq 0 ]; then
                echo "Error: Search query required"
                exit 1
            fi
            ${PACKAGE_MANAGER}_search "$@"
            ;;
        provides|whatprovides)
            if [ $# -eq 0 ]; then
                echo "Error: File name required for provides command"
                exit 1
            fi
            ${PACKAGE_MANAGER}_provides "$@"
            ;;
        list)
            if [ "$1" = "installed" ]; then
                ${PACKAGE_MANAGER}_list_installed
            else
                ${PACKAGE_MANAGER}_list "$@"
            fi
            ;;
        info)
            if [ $# -eq 0 ]; then
                echo "Error: Package name required for info command"
                exit 1
            fi
            ${PACKAGE_MANAGER}_info "$@"
            ;;
        infoweb|homepage)
            if [ $# -eq 0 ]; then
                echo "Error: Package name required for infoweb command"
                exit 1
            fi
            ${PACKAGE_MANAGER}_infoweb "$@"
            ;;
        *)
            echo "Error: Unknown command '$COMMAND'"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"