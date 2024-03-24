#!/usr/bin/env zsh

#===============================================================================
#
#          FILE:  browse-via.sh
#
#         USAGE:  ./browse-via.sh <zone> <url>
#
#   DESCRIPTION:  Create virtual machine on Google Cloud Platform and browse via it. 
#
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

source ${DOTFILES}/script/echo_color.sh

# Acquire the zone and url from the command line
if [ $# -ne 2 ]; then
    echo "Usage: $0 <zone> <url>"
    echo "Example: $0 northamerica-northeast2-a http://www.kcrt.net"
    echo "To list all the available zones, run: gcloud compute zones list"
    exit 1
fi
ZONE=$1
URL=$2

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo_error "gcloud is not installed. Please install it before running this script."
    echo_error "To install gcloud, run: curl -sSL https://sdk.cloud.google.com | bash"
    exit 1
fi

# Check if Google Chrome is not launched
if pgrep -x "Google Chrome" > /dev/null; then
    echo_error "Google Chrome is already running. Please close it before running this script."
    exit 1
fi

# Acquire current gcloud project
PROJECT=$(gcloud config get-value project)

# This machine IP
MY_IP=`curl -s http://ipinfo.io/json | jq -r '.ip'`


# check if proxy-machine exists
gcloud compute instances describe proxy-machine --zone=$ZONE
if [ $? -eq 0 ]; then
    echo_error "Virtual machine [proxy-machine] already exists."
    echo_error "Please terminate and delete it before use this script."
    echo_error "To terminate and delete the virtual machine, run: gcloud compute instances delete proxy-machine --zone=$ZONE"
    exit 1
fi

# Create a virtual machine
echo_info "Creating a virtual machine [proxy-machine] in zone [$ZONE] (project: $PROJECT)"
gcloud compute instances create proxy-machine \
    --project=$PROJECT \
    --zone=$ZONE \
    --machine-type=e2-medium \
    --network-interface=network=default,network-tier=PREMIUM,stack-type=IPV4_ONLY \
    --no-restart-on-failure \
    --maintenance-policy=TERMINATE \
    --provisioning-model=SPOT \
    --instance-termination-action=STOP \
    --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append \
    --enable-display-device \
    --create-disk=auto-delete=yes,boot=yes,device-name=instance-1,image=projects/ubuntu-os-cloud/global/images/ubuntu-2310-mantic-amd64-v20240213,mode=rw,size=10,type=projects/$PROJECT/zones/$ZONE/diskTypes/pd-balanced \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=goog-ec-src=vm_add-gcloud \
    --reservation-affinity=any

if [ $? -ne 0 ]; then
    echo_error "Failed to create the virtual machine [proxy-machine]"
    exit 1
fi

# wait for the virtual machine to be ready
echo_info "Waiting for the virtual machine [proxy-machine] to be ready... [30 sec.]"
sleep 30

# Get the external IP address of the virtual machine
VIRTUALMACHINE_IP=$(gcloud compute instances describe proxy-machine --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

# ssh into the virtual machine and install tinyproxy
echo_info "Installing tinyproxy on the virtual machine [proxy-machine]"
gcloud compute ssh proxy-machine --zone=$ZONE --command="sudo apt-get update && sudo apt-get install -y tinyproxy"
if [ $? -ne 0 ]; then
    echo_error "Failed to install tinyproxy on the virtual machine [proxy-machine]"
    exit 1
fi


# Enable and start tinyproxy
echo_info "Starting tinyproxy"
gcloud compute ssh proxy-machine --zone=$ZONE --command="sudo systemctl enable tinyproxy && sudo systemctl start tinyproxy"
if [ $? -ne 0 ]; then
    echo_error "Failed to start tinyproxy on the virtual machine [proxy-machine]"
    exit 1
fi

# Make ssh tunnel to the virtual machine
echo_info "Creating ssh tunnel to the virtual machine [proxy-machine]"
gcloud compute ssh proxy-machine --zone=$ZONE -- -S /tmp/proxy-machine-tunnel -N -f -L 8888:localhost:8888
if [ $? -ne 0 ]; then
    echo_error "Failed to create ssh tunnel to the virtual machine [proxy-machine]"
    exit 1
fi

sleep 10

# test connection
CONNECTION_IP=`env https_proxy=http://localhost:8888 http_proxy=http://localhost:8888 curl -s http://ipinfo.io/json | jq -r '.ip'`

echo_info "Current IP: $MY_IP"
echo_info "Virtual machine IP: $VIRTUALMACHINE_IP"
echo_info "Connection IP: $CONNECTION_IP"

# if vm ip is not the same as connection ip, show error
if [ "$VIRTUALMACHINE_IP" != "$CONNECTION_IP" ]; then
    echo_error "Failed to create ssh tunnel to the virtual machine [proxy-machine]"
    echo_error "Please check the virtual machine and try again."
else
    # browse via the virtual machine (use chrome)
    echo_info "Browsing via the virtual machine [proxy-machine]"
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --proxy-server="localhost:8888" $URL
fi

# terminate the ssh tunnel
echo_info "Terminating the ssh tunnel"
# gcloud compute ssh proxy-machine --zone=$ZONE -- -S /tmp/proxy-machine-tunnel -O exit
lsof -ti:8888 | xargs kill -9

# terminate the virtual machine
echo_info "Terminating the virtual machine [proxy-machine]"
gcloud compute instances delete proxy-machine --zone=$ZONE --quiet