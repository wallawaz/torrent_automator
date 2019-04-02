#!/usr/bin/bash

BITTORRENT_FOLDER="$(pwd)""/vendor/bit-torrent"
BITTORRENT_REPO=https://github.com/borzunov/bit-torrent

DEFAULT_PLATFORM=LinuxAMDx64
JACKETT_URL=https://github.com/Jackett/Jackett/releases/latest
JACKETT_FOLDER="$(pwd)""/vendor/Jackett"

# Flag for bit-torrent?

get_latest_jacket_release() {
  response=$(curl "$1")
  latest_release=$(echo "$response" | cut -d\" -f 2)
  echo "$latest_release"
}

# 1. latest_binary_url
# 2. Platform: (LinuxAMDx64, LinuxARM32, Windows..)
get_latest_binary_url() {
  response=$(curl "$1")
  grep_str="href=.*\.Binaries\.""$2"
  binary_url=$(echo "$response" | grep "$grep_str" | cut -d\" -f 2)
  echo "$binary_url"
}

binary_name() {
  echo "$1" | cut -d"/" -f 7
}

download_binary() {
  url_prefix="https://github.com"
  full_url="$url_prefix""$1"
  echo "Downloading..." $(binary_name "$1")
  wget "$full_url"
  mv $(binary_name "$1") vendor/
}

untar_binary() {
  tar_file="vendor/"$(binary_name "$1")

  if [ ! -d "$JACKETT_FOLDER" ]; then
    mkdir "$JACKETT_FOLDER"
  fi
  tar -xof "$tar_file" -C vendor/Jackett
}

download_and_untar() {
  latest_url=$(get_latest_jacket_release "$JACKETT_URL")
  echo "Downloading latest Jackett binary from $latest_url"
  latest_binary=$(get_latest_binary_url "$latest_url" "$DEFAULT_PLATFORM")
  download_binary "$latest_binary"
  untar_binary "$latest_binary"
}

install_jackett() {
  if [ ! -d "$JACKETT_FOLDER" ]; then
    echo "Jacket does not exist... downloading"
    download_and_untar
  else
    echo "Jacket already exists..."
  fi

  #./vendor/Jackett/jackett
}

install_bit_torrent() {
  if [ ! -d "$BITTORRENT_FOLDER" ]; then
    echo "bit-torrent does not exist.. cloning."
    git clone "$BITTORRENT_REPO" "$BITTORRENT_FOLDER"
  fi
  echo "Installing bit-torrent python packages."
  # make sure you are in a venv.
  python3 -m pip install -r "$BITTORRENT_FOLDER""/requirements.txt"
}

install_jackett
install_bit_torrent
