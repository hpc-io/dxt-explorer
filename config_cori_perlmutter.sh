#!/bin/sh

module load python
module load darshan
VERSION=$(which darshan-dxt-parser) 

IFS='/'
read -ra ADDR <<<"$VERSION" 

SUB='3.'
for i in "${ADDR[@]}";
do 
if [[ "$i" == *"$SUB"* ]]; then
  VERSION=$i
fi 
done  

if [[ "$VERSION" == *"3.4.0"* ]]; then
  VERSION=3.4.0.1
fi

echo "darshan==$VERSION" > constraint.txt  
