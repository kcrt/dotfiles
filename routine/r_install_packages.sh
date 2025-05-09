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

echo_info "Installing R packages..."

R --vanilla << R_UPDATE
options(repos=c(CRAN="http://cran.r-project.org"))
packages_to_need = c("tidyverse", "gtsummary", "coin", "exactRankTests", "languageserver")
packages_installed = rownames(installed.packages())
packages_to_install = packages_to_need[!is.element(packages_to_need, packages_installed)]
install.packages(packages_to_install, dependencies=TRUE)
update.packages(ask=FALSE)
R_UPDATE