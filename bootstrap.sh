#!/usr/bin/env bash

# This script is for GitHub Codespaces customization

curl -sL --proto-redir -all,https https://raw.githubusercontent.com/zplug/installer/master/installer.zsh| zsh

mkdir ~/.vim
mkdir ~/.vim/bundle
git clone --depth=1 https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim