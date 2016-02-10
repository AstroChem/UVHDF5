#!/usr/bin/env python

import argparse

parser = argparse.ArgumentParser(description="Convert CASA MS files into UVHDF5 file format.")
parser.add_argument("--MS", help="The input MS file.")
parser.add_argument("--out", default="data.hdf5", help="The output UVHDF5 file.")
parser.add_argument("--casac", action="store_true", help="Use the casac distribution instead of casapy")
args,extras = parser.parse_known_args()

import numpy as np
import sys
import shutil
import h5py

cc = 2.99792458e10 # [cm s^-1]

# Credit: parts of this file originated from the `vis_sample` repository,
# at https://github.com/AstroChem/vis_sample/blob/master/vis_sample/file_handling.py

# commands for retrieving ms data are from Sean Andrews (@seanandrews)

if args.casac:
    try:
        import casac
        tb = casac.casac.table()
        ms = casac.casac.ms()

    except ImportError:
        print("casac was not able to be imported, make sure all dependent packages are installed")
        print("try: conda install -c pkgw casa-python casa-data")
        sys.exit(1)

filename = args.MS

# Use CASA table tools to get columns of UVW, DATA, WEIGHT, etc.
tb.open(filename)
data    = tb.getcol("DATA")
uvw     = tb.getcol("UVW")
flag    = tb.getcol("FLAG")
weight  = tb.getcol("WEIGHT")
ant1    = tb.getcol("ANTENNA1")
ant2    = tb.getcol("ANTENNA2")
tb.close()

print("These are the ORIGINAL sizes of the tables in the measurement set.")
print("DATA", data.shape)
print("UVW", uvw.shape)
print("FLAG", flag.shape)
print("WEIGHT", weight.shape)

# Use CASA ms tools to get the channel/spw info
ms.open(filename)
spw_info = ms.getspectralwindowinfo()
nchan = spw_info["0"]["NumChan"]
npol = spw_info["0"]["NumCorr"]
ms.close()

# Use CASA table tools to get frequencies
tb.open(filename+"/SPECTRAL_WINDOW")
freqs = np.squeeze(tb.getcol("CHAN_FREQ"))
rfreq = tb.getcol("REF_FREQUENCY")
tb.close()

# Break out the u, v spatial frequencies (in meter units)
uu = uvw[0,:]
vv = uvw[1,:]

# u and v are measured in meters, convert to microns and then convert these to kilo-lambda
# Convert freqs to wavelengths in microns
lams = cc/freqs * 1e4 # [microns]
uu = 1e-3 * (np.tile(uu * 1e6, (nchan, 1)).T / lams).T
vv = 1e-3 * (np.tile(vv * 1e6, (nchan, 1)).T / lams).T

# Assign uniform spectral-dependence to the weights (pending CASA improvements)
sp_wgt = np.zeros_like(data.real)
# This is a (npol, nchan, nvis) shape array
# Stuff in the same weights for each channel
for i in range(nchan):
    sp_wgt[:,i,:] = weight

# (weighted) average the polarizations
real  = np.sum(data.real*sp_wgt, axis=0) / np.sum(sp_wgt, axis=0)
imag  = np.sum(data.imag*sp_wgt, axis=0) / np.sum(sp_wgt, axis=0)
weight = np.squeeze(np.sum(sp_wgt, axis=0))

# if there's only a single channel, expand this to be a (1, nvis) array
if nchan==1:
    real = Re[np.newaxis, :]
    imag = Im[np.newaxis, :]

flagged = np.any(flag, axis=(0)) # Boolean array of size (nchan, nvis)
unflagged = ~flagged # Flip so that indexing by this array gives us the good visibilities

# toss out the autocorrelation placeholders
# Flags to select only the cross-correlation values
xc = ant1 != ant2

# Now, combine the flagging indices with the autocorrelation indices
# These flags denote all visibilities that we should not be including in our likelihood calculation.
flag = ~xc & flagged

print("flag shape", flag.shape)

# uu, vv are now (nchan, nvis) shape arrays
shape = uu.shape

# Export to HDF5 format

if np.all(np.diff(freqs) > 0.0):
    dnu_pos = True
elif np.all(np.diff(freqs) < 0.0):
    dnu_pos = False
else:
    raise RuntimeError("Frequencies not in strict monotonically increasing or decreasing order.")

# Now, stuff each of these into an HDF5 file.
fid = h5py.File(args.out, "w")

# Add in observational attributes
#for key in ["OBJECT", "TELESCOP", "ORIGIN"]:
#    try:
#        val = hdr[key]
#        fid.attrs[key] = val
#    except KeyError:
#        continue

# Add in format specification version
fid.attrs["TELESCOP"] = "ALMA"
fid.attrs["FMT_Version"] = "v0.1"

# Are the frequencies stored in increasing or decreasing order in UVFITS?
# UVHDF5 always stores frequencies in increasing order
if dnu_pos:
    fid.create_dataset("freqs", (nchan,), dtype="float64")[:] = freqs # [Hz]

    fid.create_dataset("uu", shape, dtype="float64")[:,:] = uu # [kilolambda]
    fid.create_dataset("vv", shape, dtype="float64")[:,:] = vv # [kilolambda]

    fid.create_dataset("real", shape, dtype="float64")[:,:] = real # [Jy]
    fid.create_dataset("imag", shape, dtype="float64")[:,:] = imag # [Jy]

    fid.create_dataset("weight", shape, dtype="float64")[:,:] = weight #[1/Jy^2]
    fid.create_dataset("flag", shape, dtype="bool")[:,:] = flag # Boolean

else:
    print("UVFITS stored frequencies in decreasing order, flipping to positive for UVHDF5")

    fid.create_dataset("freqs", (nchan,), dtype="float64")[:] = freqs[::-1] # [Hz]

    fid.create_dataset("uu", shape, dtype="float64")[:,:] = uu[::-1] # [kilolambda]
    fid.create_dataset("vv", shape, dtype="float64")[:,:] = vv[::-1] # [kilolambda]

    fid.create_dataset("real", shape, dtype="float64")[:,:] = real[::-1] # [Jy]
    fid.create_dataset("imag", shape, dtype="float64")[:,:] = imag[::-1] # [Jy]

    fid.create_dataset("weight", shape, dtype="float64")[:,:] = weight[::-1] #[1/Jy^2]
    fid.create_dataset("flag", shape, dtype="bool")[:,:] = flag[::-1] # Boolean

fid.close()
