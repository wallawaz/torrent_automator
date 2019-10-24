#!/bin/bash

BITTORRENT_FOLDER="$(pwd)""/vendor/bit-torrent"
JACKETT_FOLDER="$(pwd)""/vendor/Jackett"

run_jackett() {
  # Starts the jackett server on default port 9117.
  # Saves the PID of the running server to file `vendor/JACKETT_PID`
  $("$JACKETT_FOLDER""/jackett") &
  JACKETT_PID=$!
  let JACKETT_PID+=1
  echo "$JACKETT_PID" > vendor/JACKETT_PID
  echo "Jackett running on port: 9117; PID:" "$JACKETT_PID"
}
run_bit_torrent() {
  python "$BITTORRENT_FOLDER""/torrent_cli.py" start &
  echo "bit-torrent running."
}
run_bit_torrent
run_jackett
