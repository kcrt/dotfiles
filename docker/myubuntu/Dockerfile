FROM ubuntu:latest
LABEL org.opencontainers.image.authors="kcrt@kcrt.net"

ENV USER kcrt

RUN apt update
RUN apt install sudo
RUN useradd -m ${USER}
RUN gpasswd -a ${USER} sudo
RUN echo "${USER}:password" | chpasswd
RUN apt-get -y install openssh-client

USER ${USER}
WORKDIR /home/${USER}
