#!/usr/bin/bash

APP_NAME="AstroPiCustoms"

echo "Updating apt"
sudo apt update -y
sudo apt upgrade -y

echo "installing wget"
sudo apt install git wget python python3-venv -y

CUR_PATH=${PWD##*/}

if [ $APP_NAME != "$CUR_PATH" ]; then
  if [ ! -d "$APP_NAME" ]; then
    echo "Cloning git repo"
    git clone https://github.com/troysworks/AstroPiCustoms.git
  fi
  echo "Changing directory"
  cd "$APP_NAME" || exit
fi

if [ -d "venv" ]; then
  echo "Creating new venv path"
  rm -rf venv
fi

echo "Upgrade pip and install venv"
python3 -m pip install --upgrade pip
python3 -m venv venv

echo "Activating venv"
source venv/bin/activate

echo "Update pip"
python -m pip install --upgrade pip

echo "Installing requirements"
pip install -r requirements.txt

echo "Installing AstroPiCustoms systemctl Service"
sudo cp astropicustoms.service /etc/systemd/system/astropicustoms.service
systemctl enable astropicustoms.service

echo "Setup complete"
