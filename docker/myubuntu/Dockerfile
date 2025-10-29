FROM ubuntu:25.04
LABEL org.opencontainers.image.authors="kcrt@kcrt.net"

ARG USER=kcrt
ARG USER_PASSWORD=password
ENV USER=${USER}

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        sudo \
        openssh-client \
        git \
        zsh \
        curl \
        vim \
        locales && \
    rm -rf /var/lib/apt/lists/* && \
    locale-gen ja_JP.UTF-8 && \
    update-locale LANG=ja_JP.UTF-8
RUN useradd -m -s /usr/bin/zsh ${USER} && \
    gpasswd -a ${USER} sudo && \
    echo "${USER}:${USER_PASSWORD}" | chpasswd && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USER} && \
    chmod 0440 /etc/sudoers.d/${USER}

RUN git clone https://github.com/kcrt/dotfiles.git /home/${USER}/dotfiles && \
    chown -R ${USER}:${USER} /home/${USER}/dotfiles

USER ${USER}
WORKDIR /home/${USER}
ENV TERM=xterm-256color
ENV ZPLUG_HOME=/home/${USER}/.zplug
ENV LANG=ja_JP.UTF-8
ENV LC_ALL=ja_JP.UTF-8
RUN git clone https://github.com/zplug/zplug $ZPLUG_HOME
RUN ~/dotfiles/script/link_dots.sh

CMD ["/usr/bin/zsh"]
