FROM kalilinux/kali-rolling:latest
LABEL org.opencontainers.image.authors="kcrt@kcrt.net"

ENV USER kcrt

RUN apt update
RUN apt install sudo
RUN useradd -m ${USER}
RUN gpasswd -a ${USER} sudo
RUN echo "${USER}:password" | chpasswd
RUN apt-get update
RUN apt-get -y install kali-linux-core kali-linux-default kali-tools-web

USER ${USER}
WORKDIR /home/${USER}
