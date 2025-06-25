#!/usr/bin/env bash

source "$HOME/dotfiles/script/echo_color.sh"

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: $0 [--help|-h]"
    echo ""
    echo "Links dotfiles from ~/dotfiles/ to the home directory."
    echo "Also links specified directories."
    echo "Backup existing files by adding .init suffix."
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    exit 0
fi

echo_info "Linking dotfiles..."
for file in ~/dotfiles/.*; do
	basename=$(basename "$file")
	# Only apply to files (ignore directories)
	if [ -f "$file" ] ; then
		target="$HOME/$basename"
		if [ -L "$target" ] && [ "$(readlink "$target")" = "$file" ]; then
			# Skip if already symlinked to the correct location
			echo_aqua "Already linked: $basename"
		elif [ -f "$target" ] && [ ! -L "$target" ]; then
			# Backup existing file if it's not a symlink
			mv "$target" "$target.init"
			ln -s "$file" "$target"
			echo_ok "Backed up and linked: $basename"
		elif [ -L "$target" ]; then
			# Show error if symlink points elsewhere
			echo_error "$target is a symlink but points to a different file: $(readlink "$target")"
		else
			ln -s "$file" "$target"
			echo_ok "Linked: $basename"
		fi
	fi
done

echo_info "Linking directories..."
candidate_dirs=(".claude")
for dir in "${candidate_dirs[@]}"; do
	source_dir="$HOME/dotfiles/$dir"
	target="$HOME/$dir"
	
	if [ -d "$source_dir" ]; then
		# Skip if already symlinked to the correct location
		if [ -L "$target" ] && [ "$(readlink "$target")" = "$source_dir" ]; then
			echo_aqua "Already linked: $dir"
		elif [ -d "$target" ] && [ ! -L "$target" ]; then
			# Backup existing directory if it's not a symlink
			mv "$target" "$target.init"
			ln -s "$source_dir" "$target"
			echo_ok "Backed up and linked: $dir"
		elif [ -L "$target" ]; then
			# Remove existing symlink if it points elsewhere
			echo_yellow "Removing mismatched symlink: $dir (pointed to $(readlink "$target"))"
			rm "$target"
			ln -s "$source_dir" "$target"
			echo_ok "Linked: $dir"
		else
			ln -s "$source_dir" "$target"
			echo_ok "Linked: $dir"
		fi
	else
		echo_error "Source directory not found: $source_dir"
	fi
done