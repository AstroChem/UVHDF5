#!/usr/bin/env python

import argparse

parser = argparse.ArgumentParser(description="Convert UVHDF5 files into CASA Measurement Set files.")
parser.add_argument("--HDF5", default="model.hdf5", help="The name of the UVHDF5 file you wish to import.")
parser.add_argument("--MS", help="The original MS data set, so that we can copy it to stuff in new values.")
parser.add_argument("--out", default="model.ms", help="The output MS dataset.")
parser.add_argument("--casac", action="store_true", help="Use the casac distribution instead of casapy")
args,extras = parser.parse_known_args()

import numpy as np
import sys
import shutil
import h5py
import os

cc = 2.99792458e10 # [cm s^-1]

# Credit: parts of this file originated from the `vis_sample` repository,
# at https://github.com/AstroChem/vis_sample/blob/master/vis_sample/file_handling.py

# CASA interfacing code comes from Peter Williams' casa-python and casa-data package
# commands for retrieving ms data are from Sean Andrews (@seanandrews)

ms_clone = args.MS
outfile = args.out

if args.casac:
    try:
        import casac
        tb = casac.casac.table()
        ms = casac.casac.ms()

    except ImportError:
        print("casac was not able to be imported, make sure all dependent packages are installed")
        print("try: conda install -c pkgw casa-python casa-data")
        sys.exit(1)

# Copy the original file so that we can then stuff our own visibilities into it
os.system("rm -rf " + outfile)
shutil.copytree(ms_clone, outfile)

# Use CASA ms tools to get the channel/spw info
ms.open(outfile)
spw_info = ms.getspectralwindowinfo()
nchan = spw_info["0"]["NumChan"]
npol = spw_info["0"]["NumCorr"]
ms.close()

# Use CASA table tools to get frequencies
tb.open(outfile + "/SPECTRAL_WINDOW")
ms_freqs = np.squeeze(tb.getcol("CHAN_FREQ"))
tb.close()

# Ascertain whether the frequencies were stored increasing or decreasing in the original MS
if np.all(np.diff(ms_freqs) > 0.0):
    dnu_pos = True
elif np.all(np.diff(ms_freqs) < 0.0):
    dnu_pos = False
else:
    raise RuntimeError("Measurement Set Frequencies not in strict monotonically increasing or decreasing order.")

# Read the model from the HDF5 file
fid = h5py.File(args.HDF5, "r")
if dnu_pos:
    freqs = fid["freqs"][:] # [Hz]
    uu = fid["uu"][:,:] # [kilolam]
    vv = fid["vv"][:,:] # [kilolam]
    real = fid["real"][:,:] # [Jy]
    imag = fid["imag"][:,:] # [Jy]
    weight = fid["weight"][:,:] #[1/Jy^2]
    flag = fid["flag"][:,:] # Bool
else:
    freqs = fid["freqs"][:][::-1] # [Hz]
    uu = fid["uu"][:][::-1,:] # [kilolam]
    vv = fid["vv"][:][::-1,:] # [kilolam]
    real = fid["real"][:][::-1,:] # [Jy]
    imag = fid["imag"][:][::-1,:] # [Jy]
    weight = fid["weight"][:][::-1,:] #[1/Jy^2]
    flag = fid["flag"][:][::-1,:] # Bool

VV = real + 1.0j * imag # [Jy]
fid.close()

# Check to make sure the frequencies of the two datasets match
assert np.allclose(freqs, ms_freqs), "Frequencies of MS and HDF5 do not match."

# Use CASA table tools to fill new DATA and WEIGHT
tb.open(outfile, nomodify=False)
data = tb.getcol("DATA")
uvw = tb.getcol("UVW")
ms_weight = tb.getcol("WEIGHT")
ms_flag = tb.getcol("FLAG")

flagged = np.any(ms_flag, axis=(0, 1)) # Boolean array of length nvis
unflagged = ~flagged # Flip so that indexing by this array gives us the good visibilities

# we need to pull the antennas and find where the autocorrelation values are and aren't
ant1    = tb.getcol("ANTENNA1")
ant2    = tb.getcol("ANTENNA2")
xc = ant1 != ant2 # indices of cross-correlations

# Now, combine the flagging indices with the autocorrelation indices
# These flags denote all visibilities that we should not be including in our likelihood calculation.
ms_flag = ~xc & flagged

# Break out the u, v spatial frequencies (in meter units)
ms_uu = uvw[0,:]
ms_vv = uvw[1,:]

# u and v are measured in meters, convert to microns and then convert these to kilo-lambda
# Convert freqs to wavelengths in microns
lams = cc/ms_freqs * 1e4 # [microns]
ms_uu = 1e-3 * (np.tile(ms_uu * 1e6, (nchan, 1)).T / lams).T
ms_vv = 1e-3 * (np.tile(ms_vv * 1e6, (nchan, 1)).T / lams).T

# Assign uniform spectral-dependence to the weights (pending CASA improvements)
sp_wgt = np.zeros_like(data.real)
# This is a (npol, nchan, nvis) shape array
# Stuff in the same weights for each channel
for i in range(nchan):
    sp_wgt[:,i,:] = ms_weight

# (weighted) average the polarizations
Wgt = np.squeeze(np.sum(sp_wgt, axis=0))

# Check to make sure that the frequencies, uu, vv, and weights are all the same from the original MS and those loaded from the HDF5.
assert np.allclose(uu, ms_uu), "UU do not match."
assert np.allclose(vv, ms_vv), "VV do not match."
assert np.allclose(weight, Wgt), "Weights do not match."
assert np.all(flag == ms_flag), "Flags do not match."

# replace the *FULL* original data with the visibilities from the HDF

# load the model file (presume this is just an array of complex numbers, with
# the appropriate sorting/ordering in original .ms file; also assume that the
# polarizations have been averaged, and that the model is unpolarized)
# Broadcasts across polarizations if there are multiple.
data[:] = VV

#data[:,:,unflagged] = VV

# put the data and weights into the MS
tb.putcol("DATA", data)

# if the MS had a corrected column, remove it (this happens with MS's created with simobserve)
if ("CORRECTED_DATA" in tb.colnames()):
    tb.removecols("CORRECTED_DATA")

tb.flush()
tb.close()
