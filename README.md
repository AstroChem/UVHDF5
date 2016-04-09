# UVHDF5 Format

A new straightforward, minimal visibility format for fitting in the UV plane.

This document describes the file format used to store visibilities for modeling in the UV plane, called the `UVHDF5` format. The first part of this document explains the format itself, then further on talks about the scripts used for reading and writing to it from CASA.

# Format Specification: Structure of a UVHDF5 file

The file is always saved with a `*.hdf5` extension, e.g. `data.hdf5`.

## Header

The following fields are optionally stored as attributes on the `/` folder of the HDF5 file.

    TARGET
    DATE
    SOFTWARE
    FORMAT (format version)

as well as *any additional* metadata that the user desires, the more the better.

## Frequencies

The frequencies are stored as a 1D array (dataset) of length `nchan` in units of Hz.

    freqs [Hz]

## Visibilities

The visibilities are stored as the following datasets on the HDF5 file, each with a shape of `(nchan, nvis)` i.e., (nrows, ncols).

    uu [kilolambda]
    vv [kilolambda]
    real [Jy]
    imag [Jy]
    weight [1/Jy^2]
    flag [Boolean mask]

The flag column is TRUE if the data point should be FLAGGED (i.e., excluded from a subsequent uv-fitting program). In general, the flag will be true for visibilities flagged in the data reduction process and for autocorrelation visibilities. 
    
# Rationale of using HDF5 (vs. NPZ and other formats)

While NPZ is readable by many scripts at the CfA already, the HDF5 file format presents many attractive features.

* HDF5 is a *universally supported standard* that can be read by programs written in other languages: Python, IDL, MATLAB, C, C++, Fortran, Julia, etc. NPZ is a python-specific format.
* HDF5 supports the use of metadata attributes, much like a FITS header. This means that extra information (e.g., name of the target, original owner of the dataset, ALMA program, CASA version, etc) can be stored inside of the visibility file itself, that way we don't get confused about provenance later on. NPZ does not support metadata, so this information can be easily lost if a file is sitting on disk for a few months or is transferred between members of the group.
* Programs like `hdf-java` allow easy visual inspection of the dataset contents (via GUI) to check that everything is in order. Checking a NPZ file field by field can be very tedious through the Python interpreter.

For now, this format has been designed around the most common type of use case: that there are the **same number of visibilities for each channel** and that the polarizations have been averaged. For more complex types of data, we will need to collaborate on a more advanced format. Please raise an issue on this github repository if you have such a use case.

# Installation

Because this format may be updated in the future, the best way to maintain the current version is to **clone this repository and add the scripts to your PATH**. In general, you will need the `h5py` python package installed on your system to read and write this format. Simple examples of doing this (perhaps for your own modeling scripts) are described next. If you would like to use the CASA measurement set and MIRIAD UVFITS export/import capabilities, please see the bottom of this document for more specific installation instructions for dependencies.

# Simple Python reading and writing

## Importing from UVHDF5 into a Python Script

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
    flag = fid["flag"]

    attributes = fid.attrs
    print(attributes)

    fid.close()

    # Do fancy stuff with visibilities here


## Exporting from a Python script to UVHDF5

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
    fid.create_dataset("flag", shape, dtype="bool")[:,:] = flag # Boolean array
    fid.close()

# Converting CASA Measurement Sets to and from UVHDF5

This step is a little more complicated, but it's mainly due to the difficulty of the many different ways CASA can be scripted. You have two options here:

1. run these scripts using your own `casapy` installation
2. run these scripts using Peter Williams' `casac` conda distribution, which is generally faster and easier to script.

Both require a little setup, so they are described separately here:

## Running using your own `casapy` distribution

This requires the python `h5py` package to be installed *into your CASA python distribution.* This can be a little tricky, since CASA bundles its own python interpreter *separate* from whatever python interpreter you have on your system (whether it be your system's python or anaconda python). The easiest way to do this is via the helper tools provided in the `casa-python` repository: https://github.com/radio-astro-tools/casa-python. Once you have installed this package, then run

    $ casa-pip install cython
    $ casa-pip install h5py

to install `cython` and then `h5py`. 

**Export from CASA measurement set to UVHDF5** is done via the `MS_to_UVHDF5.py` script. 

**Import from UVHDF5 to CASA measurement set** is done via the `UVHDF5_to_MS.py` script.

However, a frustrating complication with the `casapy` distribution is that in order to run scripts, you need to do something like

    $ casapy --nologger --nogui -c my_script.py 

which presents the problem that you need a copy of `my_script.py` in your current directory. This is generally a bad idea because if you ever need to make an update to your script, it's hard to know whether that change is propagated to all of the copies of your scripts in the various directories you made copies to. 

Thankfully, to remedy this problem you can use a trick (thanks to @elnjensen) with the `which` statement to insert the full path to your installation at runtime. 
If you already downloaded this repository and then added this to your `PATH` try

    $ which MS_to_UVHDF5.py
    > /pool/scout0/UVHDF5/MS_to_UVHDF5.py

if you added the scripts to your `PATH` correctly, you should see something similar.

**Export MS to UVHDF5**

    $ casapy --nologger --nogui -c `which MS_to_UVHDF5.py` --MS YOUR_DATA.ms --out data.hdf5

**Import UVHDF5 to MS**

    $ casapy --nologger --nogui -c `which UVHDF5_to_MS.py` --HDF5 MY_MODEL.hdf5 --MS YOUR_ORIGINAL_DATA.ms --out MY_MODEL.hdf5

## Running using CASAC distribution

First, you will need to install the `casac` distribution using 

    conda install -c pkgw casa-python casa-data

Then, you will need to install `h5py` to this particular distribution. Then, you can use the python scripts as they are, without the BASH wrapper scripts. The only potential downside to this approach is if it at some point your CASA and CASAC versions diverge across a change to the measurement set format.

**Export from CASA measurement set to UVHDF5**

    $ MS_to_UVHDF5.py --help
    usage: MS_to_UVHDF5.py [-h] [--MS MS] [--out OUT] [--casac]

    Convert CASA MS files into UVHDF5 file format.

    optional arguments:
      -h, --help  show this help message and exit
      --MS MS     The input MS file.
      --out OUT   The output UVHDF5 file.
      --casac     Use the casac distribution instead of casapy

So, you would use this like

    $ MS_to_UVHDF5.py --MS 2M1207_12CO.data.ms --casac


**UVHDF5 to CASA measurement set**

    $ UVHDF5_to_MS.py --help
    usage: UVHDF5_to_MS.py [-h] [--HDF5 HDF5] [--MS MS] [--out OUT] [--casac]

    Convert UVHDF5 files into CASA Measurement Set files.

    optional arguments:
      -h, --help   show this help message and exit
      --HDF5 HDF5  The name of the UVHDF5 file you wish to import.
      --MS MS      The original MS data set, so that we can copy it to stuff in
                   new values.
      --out OUT    The output MS dataset.
      --casac      Use the casac distribution instead of casapy

So, you would use this like
    
    $ UVHDF5_to_MS.py --HDF5 data.hdf5 --MS 2M1207_12CO.data.ms --casac

# Converting UVFITS to and from UVHDF5

If you are only exporting and importing from UVFITS files, you do not need to install CASA. However, you will need to install the `astropy` and `h5py` python packages to your system's python distribution. This does not require the `casa-python` step above and can be done with just your system pip.

Following the MIRIAD convention, these export scripts assume that any *negative* weights correspond to flagged visibilities.

**Export from UVFITS to UVHDF5**

    $ ./UVFITS_to_UVHDF5.py --help        
    usage: UVFITS_to_UVHDF5.py [-h] [--out OUT] FITS

    Convert SMA FITS files into UVHDF5 file format.

    positional arguments:
      FITS        The input UVFITS file.

    optional arguments:
      -h, --help  show this help message and exit
      --out OUT   The output UVHDF5 file

**Import from UVHDF5 to UVFITS**

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
