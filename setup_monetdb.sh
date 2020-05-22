#!/bin/bash

# Abort if some step fails.
set -e

morphStoreDir=MorphStore

cd $morphStoreDir

wget https://www.monetdb.org/downloads/sources/archive/MonetDB-11.31.13.tar.bz2
tar -xvjf MonetDB-11.31.13.tar.bz2

mkdir monetdb
cd MonetDB-11.31.13/
# MonetDB requires an absolute path.
./configure --prefix=$(pwd)/../monetdb --enable-optimize
make
make install

cd ../..
# TODO Use only one such file and the environment variable DOTMONETDBFILE.
config="user=monetdb\npassword=monetdb"
printf $config > .monetdb
printf $config > $morphStoreDir/Benchmarks/ssb/.monetdb
$morphStoreDir/monetdb/bin/monetdbd create $morphStoreDir/monetdbfarm

set +e