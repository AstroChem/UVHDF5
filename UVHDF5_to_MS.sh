#!/bin/bash

source ~/.bashrc

# This is simply a wrapper to run the UVHDF5_to_MS.py file inside of CASA.
# If you'd like, you can copy this line and execute it in your system shell.
#casapy --nologger --nogui -c UVHDF5_to_MS.py 

# Get location of installed UVHDF5 directory

if [ -z "$UVHDF5_dir" ]
then
    echo "You need to specify the location of your installed UVHDF5 scripts as an environment variable: UVHDF5_dir"
    exit
fi

echo "Reading environment variable, scripts installed in $UVHDF5_dir"

OPT_HDF5=model.hdf5
OPT_MS=data.ms
OPT_OUT=model.ms

while getopts "H:M:O:" FLAG; do
  case $FLAG in
  H)
    OPT_HDF5=$OPTARG
    ;;
  M)
    OPT_MS=$OPTARG
    ;;
  O)
    OPT_OUT=$OPTARG
    ;;
  esac
done

# Now run casapy
casapy --nologger --nogui -c $UVHDF5_dir/UVHDF5_to_MS.py --HDF5 $OPT_HDF5 --MS $OPT_MS --out $OPT_OUT

