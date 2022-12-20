FROM ubuntu:latest
LABEL org.opencontainers.image.authors="kcrt@kcrt.net"

ENV USER kcrt
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update
RUN apt-get install -y sudo openssh-client git zsh curl vim
RUN useradd -m ${USER}
RUN gpasswd -a ${USER} sudo
RUN echo "${USER}:password" | chpasswd
RUN git clone https://github.com/kcrt/dotfiles.git /home/${USER}/dotfiles

USER ${USER}
WORKDIR /home/${USER}
ENV TERM xterm-256color
ENV ZPLUG_HOME /home/${USER}/.zplug
RUN git clone https://github.com/zplug/zplug $ZPLUG_HOME
RUN ~/dotfiles/script/link_dots.sh

CMD /usr/bin/zsh
