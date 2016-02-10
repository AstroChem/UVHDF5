# UVHDF5 Format

A new straightforward, minimal visibility format for fitting in the UV plane.

This document describes the file format used to store visibilities for modeling in the UV plane, called the `UVHDF5` format.

# Export

There are scripts to export and import various datasets to this format. They are designed to be run from the command line

**Export from CASA measurement set to UVHDF5**

    $ ./MS_to_UVHDF5.py --help                                                               
    usage: MS_to_UVHDF5.py [-h] [--out OUT] MS

    Convert CASA MS files into UVHDF5 file format.

    positional arguments:
      MS          The input MS file.

    optional arguments:
      -h, --help  show this help message and exit
      --out OUT   The output UVHDF5 file.

**Export from UVFITS to UVHDF5**

    $ ./UVFITS_to_UVHDF5.py --help        
    usage: UVFITS_to_UVHDF5.py [-h] [--out OUT] FITS

    Convert SMA FITS files into UVHDF5 file format.

    positional arguments:
      FITS        The input UVFITS file.

    optional arguments:
      -h, --help  show this help message and exit
      --out OUT   The output UVHDF5 file

# Import

Since UVHDF5 is primarily a minimal format designed for fitting in the UV plane, there are minimal import capabilities. Primarily, these are designed to take *model* and *residual* visibilities produced from fits to an exported dataset and recreate a dataset in the same CASA MS or UVFITS format. This way, the MS or UVFITS file can be imaged (CLEANed) in the same way as the data.

**UVHDF5 to CASA measurement set**

    $ ./UVHDF5_to_MS.py --help                  
    usage: UVHDF5_to_MS.py [-h] [--out OUT] HDF5 MS

    Convert UVHDF5 files into UVFITS files.

    positional arguments:
      HDF5        The name of the UVHDF5 file you wish to import.
      MS          The original MS data set, so that we can copy it to stuff in new
                  values.

    optional arguments:
      -h, --help  show this help message and exit
      --out OUT   The output MS dataset.

**UVHDF5 to UVFITS**

    $ ./UVHDF5_to_UVFITS.py --help    
    usage: UVHDF5_to_UVFITS.py [-h] [--out OUT] HDF5 FITS

    Convert UVHDF5 files into UVFITS files.

    positional arguments:
      HDF5        The name of the UVHDF5 file you wish to import.
      FITS        The original FITS data set, so that we can copy it to stuff in
                  new values.

    optional arguments:
      -h, --help  show this help message and exit
      --out OUT   The output FITS file

# Format Specification: Structure of a UVHDF5 file

The file is always saved with a `*.hdf5` extension, e.g. `data.hdf5`.

## Header

The following fields are optionally stored as attributes on the `/` folder of the HDF5 file.

    Target Name
    Creation Date
    Reduction Software (name and version)
    Format Spec Version (vis_sample version)

as well as any additional metadata that the user desires.

## Frequencies

The frequencies are stored as a 1D array of length `nchan` in units of Hz.

    freqs [Hz]

## Visibilities

The visibilities are stored as the following datasets on the HDF5 file, each with a shape of `(nchan, nvis)` nrows X ncols.

    uu [kilolambda]
    vv [kilolambda]
    real [Jy]
    imag [Jy]
    weight [1/Jy^2]

Some limitations of this format:

* Only unflagged data can be stored.
* No autocorrelation data can be stored (for now).

# Rationale of using HDF5 (vs. NPZ and other formats)

While NPZ is readily readable by many scripts at the CfA already, the HDF5 file format presents many attractive features.

* HDF5 is a universally supported standard that can be read by programs written in other languages: Python, IDL, MATLAB, C, C++, Fortran, Julia, etc. NPZ is a python-specific format.
* HDF5 supports the use of metadata attributes, much like a FITS header. This means that extra information (e.g., name of the target, original owner of the dataset, ALMA program of observation, reduction version) can be stored inside of the visibility file itself so that we don't get confused about provenance later on. NPZ does not support metadata, so this information can be easily lost if a file is sitting on disk for a few months or is transferred between members of the group.
* Programs like `hdf-java` allow easy visual inspection of the dataset contents (via GUI) to check that everything is in order. Checking a NPZ file field by field can be very tedious through the Python interpreter.

For now, this format has been designed around the most common type of use case: that there are the **same number of visibilities for each channel**. For more complex types of data, we will need to collaborate on a more advanced format.


# Reading from UVHDF5 in a Python Script

Here is an example snippet of python code that would be useful to read this new file format into your own analysis code in Python. This requires that you have installed the `h5py` python package.

    import h5py
    import numpy as np

    filename = "data.hdf5"

    fid = h5py.File(filename, "r")
    freqs = fid["freqs"][:] # [Hz]
    uu = fid["uu"][:,:] # [kilolam]
    vv = fid["vv"][:,:] # [kilolam]
    real = fid["real"][:,:] # [Jy]
    imag = fid["imag"][:,:] # [Jy]
    weight = fid["weight"][:,:] #[1/Jy^2]

    attributes = fid.attrs
    print(attributes)

    fid.close()

    # Do fancy stuff with visibilities here


# Writing to UVHDF5

Here is an example of how to write your dataset to this file format in Python.

    # Assume that you have your frequencies stored in a 1D array of length `nfreq`
    # and that you have your visibilities stored in 2D arrays of size `(nfreq, nvis)`.

    shape = (nfreq, nvis)

    import h5py

    filename = "model.hdf5"

    fid = h5py.File(filename, "w")

    fid.attrs["OBJECT"] = "My target" # attributes are added like dictionary values in Python

    fid.create_dataset("freqs", (nfreq,), dtype="float64")[:] = freqs # [Hz]

    fid.create_dataset("uu", shape, dtype="float64")[:,:] = uu # [kilolambda]
    fid.create_dataset("vv", shape, dtype="float64")[:,:] = vv # [kilolambda]

    fid.create_dataset("real", shape, dtype="float64")[:,:] = real # [Jy]
    fid.create_dataset("imag", shape, dtype="float64")[:,:] = imag # [Jy]

    fid.create_dataset("weight", shape, dtype="float64")[:,:] = weight #[1/Jy^2]
    fid.close()
