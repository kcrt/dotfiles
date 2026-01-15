#
#	067-functions_docker.zsh
#		Docker aliases and functions
#

abbrev-alias docker_busybox="docker run -it --rm busybox"
abbrev-alias docker_busybox_mount_home="docker run -it --rm -v $HOME:/root busybox"
abbrev-alias docker_busybox_mount_home_readonly="docker run -it --rm -v $HOME:/root:ro busybox"
abbrev-alias docker_alpine="docker run -it --rm alpine"
abbrev-alias docker_alpine_mount_home="docker run -it --rm -v $HOME:/root alpine"
abbrev-alias docker_alpine_mount_home_readonly="docker run -it --rm -v $HOME:/root:ro alpine"
abbrev-alias docker_ubuntu="docker run -it --rm ubuntu"
abbrev-alias docker_ubuntu_x86="docker run -it --platform linux/amd64 --rm ubuntu"
abbrev-alias docker_ubuntu_mount_home="docker run -it --rm -v $HOME:/root ubuntu"
abbrev-alias docker_mykali="docker build --tag mykali ${DOTFILES}/docker/mykali/; docker run -it --rm --hostname='mykali' --name='mykali' -v ~/.ssh/:/home/$USER/.ssh/:ro -v ${DOTFILES}/:/home/$USER/dotfiles:ro mykali"
abbrev-alias docker_myubuntu="nocorrect docker build --tag myubuntu ${DOTFILES}/docker/myubuntu/; docker run -it --rm --hostname='myubuntu' --name='myubuntu' -v $HOME:/container:ro -v $HOME/workspace:/workspace myubuntu"
abbrev-alias docker_secretlint='docker run -v `pwd`:`pwd` -w `pwd` --rm -it secretlint/secretlint secretlint "**/*"'
abbrev-alias docker_lazydocker='docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock -v /yourpath:/.config/jesseduffield/lazydocker lazyteam/lazydocker'
