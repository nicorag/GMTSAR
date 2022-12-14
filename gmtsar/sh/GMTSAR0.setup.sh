#!/bin/sh
# Alexey Pechnikov, Aug, 2021, https://github.com/mobigroup/gmtsar
# See "General Setup" in https://topex.ucsd.edu/gmtsar/tar/sentinel_time_series_3.pdf
# use after GMTSAR.install.sh and GMTSAR.data_orbit.sh next
# ./GMTSAR.setup.sh /home/jupyter/GMTSAR /home/jupyter/DEM/dem.grd
set -e

workdir="$1"
demfile="$2"
rdec="$3"
adec="$4"
defomax="$5"
wlength="$6"

# cleanup from previous runs
rm -fr "$workdir"
mkdir -p "$workdir"
cd "$workdir"

for orbit in asc dsc
do
    mkdir -p "$orbit"
    cd "$orbit"
    mkdir -p data orbit reframed topo SBAS merge
    cd topo
    #cp "$demfile" dem.grd
    gdal_translate -of NetCDF -ot Float32 -co FORMAT=NC4C -co COMPRESS=DEFLATE -co ZLEVEL=3 -a_nodata nan "$demfile" dem.grd
    cd ..
    cd merge
    ln -f -s ../topo/dem.grd .
    cd ..
    for swath in F1 F2 F3
    do
        mkdir -p "$swath"
        cd "$swath"
        mkdir -p raw SLC intf_in topo
        cd topo
        ln -f -s ../../topo/dem.grd .
        cd ..
        cp /usr/local/GMTSAR/gmtsar/csh/batch_tops.config .
        # see page 16 "Run One Interferogram to Test Settings"
        # for now, only threshold_geocode changed from 0.12 to 0 by the code below
        sed -i -s "s/^proc_stage.*\$/proc_stage = 1/g"                                  batch_tops.config
        sed -i -s "s/^shift_topo.*\$/shift_topo = 0/g"                                  batch_tops.config
        sed -i -s "s/^filter_wavelength.*\$/filter_wavelength = ${wlength}/g"           batch_tops.config
        # this option does not work
#        if [ -z "${GMTSAR_LANDMASK}" ]
#        then
#            echo "Set the landmask to be 0 (GMTSAR_LANDMASK=${GMTSAR_LANDMASK})"
#            sed -i -s "s/^switch_land.*\$/switch_land = 0/g"                            batch_tops.config
#        else
#            echo "Set the landmask to be 1 (GMTSAR_LANDMASK=${GMTSAR_LANDMASK})"
#            sed -i -s "s/^switch_land.*\$/switch_land = 1/g"                            batch_tops.config
#        fi
        # see https://github.com/gmtsar/gmtsar/issues/192
        if [ -n "$rdec" -a -n "$adec" ]
        then
            echo "Set the decimation to be 2 for images with smaller file size"
            sed -i -s "s/^dec_factor.*\$/dec_factor = 2/g"                              batch_tops.config
            sed -i -s "s/^range_dec.*\$/range_dec = ${rdec}/g"                          batch_tops.config
            sed -i -s "s/^azimuth_dec.*\$/azimuth_dec = ${adec}/g"                      batch_tops.config
        else
            echo "Set the decimation to be 1 if you want higher resolution images"
            sed -i -s "s/^dec_factor.*\$/dec_factor = 1/g"                              batch_tops.config
            sed -i -s "s/^range_dec.*\$/range_dec = 1/g"                                batch_tops.config
            sed -i -s "s/^azimuth_dec.*\$/azimuth_dec = 1/g"                            batch_tops.config
        fi
        sed -i -s "s/^threshold_snaphu.*\$/threshold_snaphu = 0/g"                      batch_tops.config
        if [ -z "${defomax}" ]
        then
            echo "Set defo_max = 0 - used for smooth unwrapped phase such as interseismic deformation, no phase jumps"
            sed -i -s "s/^defomax.*\$/defomax = 0/g"                                    batch_tops.config
        else
            echo "Set defo_max = ${defomax} - will allow a phase jump, cycles"
            sed -i -s "s/^defomax.*\$/defomax = ${GMTSAR_DEFOMAX}/g"                    batch_tops.config
        fi
        sed -i -s "s/^threshold_geocode.*\$/threshold_geocode = 0/g"                    batch_tops.config
        # return
        cd ..
    done
    cd ..
done
