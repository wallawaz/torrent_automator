#!/usr/bin/bash

BITTORRENT_FOLDER="$(pwd)""/vendor/bit-torrent"
JACKETT_FOLDER="$(pwd)""/vendor/Jackett"

stop_jackett() {
  # Stops the jackett server using the saved `vendor/JACKETT_PID` file.
  JACKETT_PID=$(cat vendor/JACKETT_PID)
  kill -9 "$JACKETT_PID"
  rm vendor/JACKETT_PID
  echo jackett stopped.
}
stop_bit_torrent() {
  python "$BITTORRENT_FOLDER""/torrent_cli.py" stop 
  echo bit-torrent stopped.
}
stop_bit_torrent
stop_jackett
