#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  mainmac.sh
#         USAGE:  source ${DOTFILES}/script/mainmac.sh
#   DESCRIPTION:  Which Mac is the main machine, for maintain.sh and the
#                 routine/mainmac_*.sh scripts.
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

# The main Mac is the only one that pushes to the NAS. The backup mirrors with
# --delete, so two Macs running it would delete each other's files there.
# When moving to a new Mac, change this line (and nothing else).
MAIN_MAC_HOST=silicon

# is_main_mac -> 0 on the main Mac
#
# macOS hands back "silicon" or "silicon.local" for $HOST depending on mDNS,
# so the suffix is dropped before comparing.
function is_main_mac(){
	[[ "${HOST%.local}" == "$MAIN_MAC_HOST" ]]
}
