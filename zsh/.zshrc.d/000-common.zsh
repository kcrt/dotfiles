#
#	001-startup.zsh
#		Common utility functions for zsh configuration
#

# ------------------------------------------------------------------------------
# File age checking utilities
# ------------------------------------------------------------------------------
# Check if a file is older than specified seconds
# Usage: is_file_older_than_seconds <file_path> <seconds>
# Returns: 0 if file is older, 1 otherwise
is_file_older_than_seconds() {
	local file_path="$1"
	local max_age_seconds="$2"

	# File doesn't exist = should regenerate
	[[ ! -f "$file_path" ]] && return 0

	# Get file modification time (epoch seconds)
	local file_epoch
	if [[ "$OSTYPE" = darwin* ]]; then
		file_epoch=$(stat -f '%m' "$file_path" 2>/dev/null)
	else
		file_epoch=$(stat -c '%Y' "$file_path" 2>/dev/null)
	fi

	# If stat failed, assume file is old
	[[ -z "$file_epoch" ]] && return 0

	# Check if file is older than max_age_seconds
	local now_epoch=$(date +%s)
	local file_age=$(( now_epoch - file_epoch ))
	[[ $file_age -gt $max_age_seconds ]] && return 0
	return 1
}

# Check if a file is older than specified days
# Usage: is_file_older_than_days <file_path> <days>
# Returns: 0 if file is older, 1 otherwise
is_file_older_than_days() {
	local file_path="$1"
	local max_age_days="$2"
	local max_age_seconds=$(( max_age_days * 86400 ))
	is_file_older_than_seconds "$file_path" "$max_age_seconds"
}
