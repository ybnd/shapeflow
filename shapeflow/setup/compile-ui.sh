#!/bin/bash

OG_PWD=$(pwd)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT="$DIR/../../"

cd $ROOT || exit
VERSION=$(python sf.py --version)

cd ui || exit

npm install && npm audit fix && npm run generate && tar -czvf "dist-$VERSION.tar.gz" "dist"

cd $OG_PWD || exit
