#!/bin/sh

VERSION=$(pkg-config --modversion darshan-util) 
echo "darshan==$VERSION.*" > constraints.txt
