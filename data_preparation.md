# Preparation

This repository provides scripts to export the visibilities contained in a CASA measurement set (MS) to the UVHDF5 file format. These scripts are quite limited, they literally use CASA table tools to copy the visibilities, e.g.,

    data    = tb.getcol("DATA")
    uvw     = tb.getcol("UVW")
    flag    = tb.getcol("FLAG")
    weight  = tb.getcol("WEIGHT")
    ant1    = tb.getcol("ANTENNA1")
    ant2    = tb.getcol("ANTENNA2")

and currently assume that there is only one spectral window, the one with your data. Needless to say, most raw datasets will need to go through some processing before they can be used with these scripts. These processing steps should be familiar to most CASA users, but they are summarized here for guidance.

## Apply the pipeline calibration

If you are the P.I. of the data, and you downloaded the final, calibrated measurement set from the NAASC, you can skip this step. Otherwise, you'll need to apply the calibrations by running ``scriptForPI.py`` located in the `scripts/` directory of your giant tarball. Instructions for Cycle 5 data are available [here](https://casaguides.nrao.edu/index.php/ALMA_Cycle_5_Imaging_Pipeline_Reprocessing#Restore_Pipeline_Calibration_and_Prepare_for_Re-imaging_.28all_Options.29), and other cycles are available on casaguides. As always, when you first get the data it's a good idea to run `listobs` in CASA just to review the metadata and see what you're dealing with.

## Run the imaging scripts

Although UVHDF5 only deals with the visibilities, it's a very good idea to go through the full imaging process to make sure we understand what the data that we're exporting actually looks like in the image plane. A good starting point is the ``scriptForImaging.py`` located in the `scripts/` directory. You will likely want to open this script up and tweak some of the parameters. A guide to this script is available [here](https://casaguides.nrao.edu/index.php/Guide_to_the_NA_Imaging_Template).

For example, if you have observed a protoplanetary disk in a standard spectral setup, a common operation will be to run [self-calibration](https://casaguides.nrao.edu/index.php/Self-Calibration_Template) on the (strong) dust continuum. For molecular line emission, you'll generally want to [subtract the dust continuum and then apply the self-calibration solution](https://casaguides.nrao.edu/index.php/Image_Line).

All of these options are most likely in the ``scriptForImaging.py`` file, though you may need to uncomment some tasks and change some parameters to suit your dataset.

You'll also want to make some images of the dust and line emission using [`tclean`](https://casaguides.nrao.edu/index.php/TCLEAN_and_ALMA). If you're exporting line emission of a protoplanetary disk, you'll most likely want to make some changes to the default `tclean` parameters. You'll probably want to reduce the size of the image to cover just the disk (a few arcseconds in size) to speed up the imaging, and then you'll also want to note which channels actually have line emission, and which are empty. For more information on these choices, see the [`tclean` docs](https://casa.nrao.edu/casadocs/casa-5.1.2/synthesis-imaging/spectral-line-imaging). The important thing to note at this step is which channels actually have emission. Depending on what correlator setup you chose for the observation, there may be many channels which don't have any disk emission, and we'll want to exclude those from being exported. Similarly, if you observed your disk at very fine spectral resolution, we may want to average channels together to save on datasize (see below).

If you have a large dataset, be aware that running through all of these preparation steps can take a full day to run on a normal laptop.

If you do want to fiddle around with the velocity channels, just to get a handle on where the emission is, in `tclean` you can specify the `restfreq` of some common lines, and then specify start="-10km/s", nchan=100, or some velocity relative to your expected line.

    12CO 2-1: 230.538 GHz
    12CO 3-2: 345.79599 GHz
    13CO 2-1: 220.39868 GHz
    13CO 3-2: 330.58797 GHz
    C18O 2-1: 219.56036 GHz


## Velocity frames, averaging channels, and split

Because ALMA does not Doppler track (see this [VLA note](https://science.nrao.edu/facilities/vla/docs/manuals/obsguide/modes/line) for more information on the concept), the data are acquired in the `TOPO` or Earth-based reference frame, where the frequency of the channels is that specified at the beginning of the observation. By default, the visibilities in your CASA measurement set are stored in this topocentric reference frame (`TOPO`) at fixed sky frequency. In this frame, Earth-based RFI will show up in the same channels, but molecular emission from an astrophysical source will change velocities over the course of an observation (due to the Earth's rotation and orbital motion). For short, contiguous integrations (few hours), this line shift is small < 0.5 km/s. If the scheduling block executions of your program were on different days, or at different times of the year, however, then this effect can be as large as the Earth's orbital motion around the sun (30 km/s). Generally, this issue is swept under the rug when we use `tclean`, because we can specify which frame we would like the image channels to be in (e.g., LSRK, Barycentric, etc...), and CASA seamlessly handles the velocity transformations for us. LSRK is the CASA default reference frame.

If you plan to export visbilities without correcting for this there are two things you'll need to consider. One: if you're observation is short (< 1-2 hours), then the total velocity shift in visbilities is likely small (< 0.5 km/s), but if it's longer, then you should be worried. Two: the systemic source velocity of the visibilities will be in the topocentric frame, which is essentially a meaningless quantity for any astrophysical velocity comparison, since it's dependent on the time of observation. If you're goal is to compare (or check) the source velocity against pre-established redshift or radial velocity measurements, you're going to need to do the conversion from `TOPO` to your frame of choice at some point, so you might as well do it now with CASA's built in tools. For sources like protoplanetary disks, I've found the most useful to be `BARY`, or the barycentric frame of our solar system.

The way correct the velocity of the visibilities is using CASA's `mstransform` task. In addition to the  [help](https://casa.nrao.edu/casadocs/casa-5.1.2/global-task-list/task_mstransform/about) page, there is a good [primer](https://casa.nrao.edu/casadocs/casa-5.0.0/uv-manipulation/manipulating-visibilities-with-mstransform) on using `mstransform`.

If you saw that you had more than 20 channels across the full disk width, you may want to consider averaging some channels together to save on the final data rate. You'll likely want to joint this together into a single `mstransform` call, since it will save I/O time. You may need to adjust `vis` and `spw` to select the data you want. You'll also want to limit the export region using `start` and `nchan`. If averaging, you can also use `width`.

And, when exporting the visibilities, it's easiest if your measurement set is as simple as possible, containing *only* the visibilities for the line that you're using `UVHDF5` to model. That way, we don't need to worry about other spectral windows or possibly affecting unrelated data. This can also be accomplished by `mstransform` (as well as `split`). E.g., a typical `mstransform` call might look like


    mstransform(vis="myMeasurementSet.ms.contsub",
    outputvis="myMeasurementSet.avg.tbin.ms",
    spw="1", # the spw reflecting your data in myMeasurementSet.ms.contsub
    regridms=True, # we will be changing velocities
    outframe="bary", # select the Barycentric velocity reference frame
    timeaverage=True,
    timebin = '18s', # average the visibilities in 18s blocks.
    restfreq="345.79599GHz", # resf-frequency of our line, 12CO J=3-2
    mode="velocity",
    start="14.0km/s", # starting velocity, relative to restfreq. The reason this is larger than 0 is the large radial
    # velocity of our source
    nchan=33, # export 33 channels
    width="0.2km/s", # the default res of our data is 0.05 km/s, so we'll average by a factor of 4.
    datacolumn="data")

Once exported, it's always a good idea to image the exported MS (`myMeasurementSet.avg.tbin.ms`) with `tclean` just to see that you really have exported the data that you want.
