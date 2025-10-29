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
        locales \
        unzip && \
    rm -rf /var/lib/apt/lists/* && \
    locale-gen ja_JP.UTF-8 && \
    update-locale LANG=ja_JP.UTF-8
RUN useradd -m -s /usr/bin/zsh ${USER} && \
    gpasswd -a ${USER} sudo && \
    echo "${USER}:${USER_PASSWORD}" | chpasswd && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USER} && \
    chmod 0440 /etc/sudoers.d/${USER}

USER ${USER}
WORKDIR /home/${USER}
ENV TERM=xterm-256color
ENV LANG=ja_JP.UTF-8
ENV LC_ALL=ja_JP.UTF-8

RUN git clone --depth=1 https://github.com/kcrt/dotfiles.git /home/${USER}/dotfiles && \
    chown -R ${USER}:${USER} /home/${USER}/dotfiles

# Install sheldon (plugin manager for zsh) and set up dotfiles
RUN curl --proto '=https' -fLsS https://rossmacarthur.github.io/install/crate.sh | bash -s -- --repo rossmacarthur/sheldon --to /home/${USER}/.local/bin && \
    mkdir -p /home/${USER}/.config/sheldon && \
    ln -sf /home/${USER}/dotfiles/sheldon/plugins.toml /home/${USER}/.config/sheldon/plugins.toml && \
    /home/${USER}/.local/bin/sheldon lock --update && \
    ~/dotfiles/script/link_dots.sh

CMD ["/usr/bin/zsh"]
