#!/bin/bash

source ~/.bashrc

# This is simply to run the MS_to_UVHDF5.py file inside of CASA. 
# If you'd like, you can copy this line and execute it in your system shell.
#casapy --nologger --nogui -c MS_to_UVHDF5.py --MS $1 

# Get location of installed UVHDF5 directory

if [ -z "$UVHDF5_dir" ]
then
    echo "You need to specify the location of your installed UVHDF5 scripts as an environment variable: UVHDF5_dir"
    exit
fi

echo "Reading environment variable, scripts installed in $UVHDF5_dir"

OPT_MS=data.ms
OPT_OUT=data.hdf5

while getopts "M:O:" FLAG; do
  case $FLAG in
  M)
    OPT_MS=$OPTARG
    ;;
  O)
    OPT_OUT=$OPTARG
    ;;
  esac
done

# Now run casapy
casapy --nologger --nogui -c $UVHDF5_dir/MS_to_UVHDF5.py --MS $OPT_MS --out $OPT_OUT

