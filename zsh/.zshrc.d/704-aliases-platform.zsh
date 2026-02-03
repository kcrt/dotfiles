#
# 704-aliases-platform.zsh
#   Platform-specific aliases (Wine, Azure, etc.)
#

# ============================================================================
# Azure
# ============================================================================

alias azure_neon_start='az vm start --resource-group neon_group --name neon'
alias azure_neon_stop='az vm stop --resource-group neon_group --name neon; az vm deallocate --resource-group neon_group --name neon'

# ============================================================================
# Wine (macOS only)
# ============================================================================

export WINEPREFIX="$HOME/.wine"
if [[ "$OSTYPE" = *darwin* ]]; then
	abbrev-alias wine_steam='wine64 ~/.wine/drive_c/Program\ Files\ \(x86\)/Steam/Steam.exe -no-cef-sandbox'
	# abbrev-alias wine_gameportingkit='LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8 MTL_HUD_ENABLED=1 WINEESYNC=1 `arch -x86_64 brew --prefix game-porting-toolkit`/bin/wine64'
	alias -s exe='wine'
fi
