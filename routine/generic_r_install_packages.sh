#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  r_install_packages.sh
#         USAGE:  ./r_install_packages.sh
#   DESCRIPTION:  Install packages for R.
#                 Use this script after installing/upgrading R.
#  REQUIREMENTS:  r
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/OSNotify.sh

if ! command -v R > /dev/null 2>&1; then
    OSError "R is not installed. Please install it first."
    exit 1
fi

echo_info "Installing R packages..."

# The delimiter is quoted so the shell leaves the R code alone.
R --vanilla << 'R_UPDATE'
options(repos=c(CRAN="http://cran.r-project.org"))
packages_to_need = c("tidyverse", "gtsummary", "coin", "exactRankTests", "languageserver")
packages_installed = rownames(installed.packages())
packages_to_install = packages_to_need[!is.element(packages_to_need, packages_installed)]
install.packages(packages_to_install, dependencies=TRUE)
update.packages(ask=FALSE)
R_UPDATE
r_status=$?
(( r_status == 0 )) || count_failure "R package update failed (exit $r_status)."

routine_exit_status