#!/usr/bin/env bash
set -e

path1=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
path2=$(dirname "$0")

echo "USING COMPLICATED: $path1"
echo "USING DIRNAME $path2"