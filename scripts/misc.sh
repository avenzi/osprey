#!/usr/bin/env bash

# Function that waits on a given subproces, outputting a loading message
# Inteded use:
# (command1; command2; ...) > /dev/null &; loading $! "Loading Message";
# $1 is a PID to wait on
# $2 is a loading message
loading() {
  printf "%b\n" "$2"  # show loading message
  tput civis  # hide cursor
  stty -echo  # disable user input
  trap "tput cnorm; stty sane" exit return  # enable user input and show cursor
  wait $1
  return
}