#!/usr/bin/env python3
# Alexey Pechnikov, Sep, 2021, https://github.com/mobigroup/gmtsar
# python3 -m pip install install pandas --upgrade
# Wrapper to scan *xml files and orbits and make data.in file like to prep_data_linux.csh & prep_data.csh tools
#import pytest

class SBAS:

    def __repr__(self):
        return 'Object %s %d items\n%r' % (self.__class__.__name__, len(self.df), self.df)

    def __init__(self, datadir, dem_filename, basedir):
        import os
        from glob import glob
        import pandas as pd
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        oneday = relativedelta(days=1)

        self.dem_filename = os.path.relpath(dem_filename,'.')
        #print ('dem_filename', self.dem_filename)

        # master image
        self.master = None
        
        # processing directory
        self.basedir = basedir

        orbits = glob(os.path.join(datadir, 'S1?*.EOF'), recursive=True)
        orbits = pd.DataFrame(orbits, columns=['orbitpath'])
        orbits['orbitfile'] = [os.path.split(file)[-1] for file in orbits['orbitpath']]
        orbits['orbitname'] = [os.path.splitext(name)[0] for name in orbits['orbitfile']]
        orbits['date1'] = [name.split('_')[-2][1:9] for name in orbits['orbitname']]
        orbits['date2'] = [name.split('_')[-1][:8] for name in orbits['orbitname']]
        #print (orbits)

        metas = glob(os.path.join(datadir, 's1?-iw*.xml'), recursive=True)
        metas = pd.DataFrame(metas, columns=['metapath'])
        metas['metafile'] = [os.path.split(file)[-1] for file in metas['metapath']]
        metas['filename'] = [os.path.splitext(file)[0] for file in metas['metafile']]
        dates = [name[15:30] for name in metas['metafile']]
        dates = [datetime.strptime(date, "%Y%m%dt%H%M%S") for date in dates]
        #print (dates)
        metas['date'] = [date.strftime("%Y-%m-%d") for date in dates]
        metas['date1'] = [(date-oneday).strftime("%Y%m%d") for date in dates]
        metas['date2'] = [(date+oneday).strftime("%Y%m%d") for date in dates]
        #print (filenames)
        #metanames['data'] = [filename[:-4]+'.tiff' for metaname in metanames['metaname']]
        #metanames['dataname'] = [basename[:-4]+'.tiff' for basename in metanames['basename']]
        # TODO: replace F1 to iw*
        metas['stem'] = [f'S1_{date.strftime("%Y%m%d_%H%M%S")}_F1' for date in dates]
        metas['multistem'] = [f'S1_{date.strftime("%Y%m%d")}_ALL_F1' for date in dates]

        datas = glob(os.path.join(datadir, 's1?-iw*.tiff'), recursive=True)
        datas = pd.DataFrame(datas, columns=['datapath'])
        datas['datafile'] = [os.path.split(file)[-1] for file in datas['datapath']]
        datas['filename'] = [os.path.splitext(file)[0] for file in datas['datafile']]
        #print (datas)

        self.df = pd.merge(metas, orbits,  how='left', left_on=['date1','date2'], right_on = ['date1','date2'])
        self.df = pd.merge(self.df, datas,  how='left', left_on=['filename'], right_on = ['filename']).set_index('date')
        del self.df['date1']
        del self.df['date2']

    def set_master(self, master):
        self.master = master
        return self

    def get_master(self):
        if self.master is None:
            raise Exception('Set master image first')
        idx = self.master
        return self.df.loc[[idx]]

    def get_aligned(self, date=None):
        if self.master is None:
            raise Exception('Set master image first')
        #if self.master is not None and self.master == date:
        #    raise Exception('Requested image is master image')

        if date is None:
            idx = self.df.index.difference([self.master])
        else:
            idx = [date]
        return self.df.loc[idx]

    def to_file(self, filename):
        """
        Save data.in file like to prep_data_linux.csh & prep_data.csh tools
        """
        if self.master is None:
            raise Exception('Set master image first')
        line = '\n'.join(self.get_master().apply(lambda row: f'{row.filename}:{row.orbitfile}', axis=1).values)
        lines = '\n'.join(self.get_aligned().apply(lambda row: f'{row.filename}:{row.orbitfile}', axis=1).values)
        with open(filename, 'wt') as f:
            f.write(line+'\n'+lines+'\n')
        return self

    def geoloc(self, date=None):
        import pandas as pd
        import xmltodict

        if date is None:
            if self.master is None:
                raise Exception('Set master image or define argument date')
            date = self.master

        filename = self.df.loc[date,'metapath']
        with open(filename) as fd:
            doc = xmltodict.parse(fd.read())
        #doc['geolocationGrid']
        geoloc = doc['product']['geolocationGrid']['geolocationGridPointList']
        # check data consistency
        assert int(geoloc['@count']) == len(geoloc['geolocationGridPoint'])
        geoloc_df = pd.DataFrame(geoloc['geolocationGridPoint']).applymap(lambda val : pd.to_numeric(val,errors='ignore'))
        return geoloc_df
    
    def get_dem(self, geoloc=False, buffer_degrees = 0):
        import xarray as xr
                
        dem = xr.open_dataarray(self.dem_filename)
        if geoloc is False:
            return dem
        
        geoloc = self.geoloc()
        ymin, ymax = geoloc.latitude.min(), geoloc.latitude.max()
        #print ('ymin, ymax', ymin, ymax)
        xmin, xmax = geoloc.longitude.min(), geoloc.longitude.max()
        #print ('xmin, xmax', xmin, xmax)
        return dem.sel(lat=slice(ymin-buffer_degrees, ymax+buffer_degrees),
                       lon=slice(xmin-buffer_degrees, xmax+buffer_degrees))

    # replacement for gmt grdfilter ../topo/dem.grd -D2 -Fg2 -I12s -Gflt.grd
    def get_topo_llt(self, degrees, geoloc=True):
        import xarray as xr
        import numpy as np

        # add buffer around the cropped area for borders interpolation
        dem_area = self.get_dem(geoloc=geoloc, buffer_degrees=2*degrees)
        ny = int(np.round(degrees/dem_area.lat.diff('lat')[0]))
        nx = int(np.round(degrees/dem_area.lon.diff('lon')[0]))
        #print ('DEM decimation','ny', ny, 'nx', nx)
        dem_area = dem_area.coarsen({'lat': ny, 'lon': nx}, boundary='pad').mean()

        lats, lons, z = xr.broadcast(dem_area.lat, dem_area.lon, dem_area)
        topo_llt = np.column_stack([lons.values.ravel(), lats.values.ravel(), z.values.ravel()])
        return topo_llt

    def offset2shift(self, xyz, rmax, amax):
        import xarray as xr
        import numpy as np
        from scipy.interpolate import griddata

        # use center pixel GMT registration mode
        rngs = np.arange(8/2, rmax+8/2, 8)
        azis = np.arange(4/2, amax+4/2, 4)
        grid_r, grid_a = np.meshgrid(rngs, azis)

        grid = griddata((xyz[:,0], xyz[:,1]), xyz[:,2], (grid_r, grid_a), method='cubic')
        da = xr.DataArray(np.flipud(grid), coords={'y': azis, 'x': rngs}, name='z')
        return da

    def to_dataframe(self):
        return self.df

    def ext_orb_s1a(self, stem, date=None):
        import os
        import subprocess

        if date is None or date == self.master:
            df = self.get_master()
        else:
            df = self.df.loc[[date]]

        orbit = os.path.relpath(df['orbitpath'][0], self.basedir)
    
        argv = ['ext_orb_s1a', f'{stem}.PRM', orbit, stem]
        #print ('argv', argv)
        p = subprocess.Popen(argv, stderr=subprocess.PIPE, cwd=self.basedir)
        stderr_data = p.communicate()[1]
        if len(stderr_data) > 0:
            print (stderr_data.decode('ascii'))
        return
    
    # produce LED and PRM in basedir
    # when date=None work on master image
    def make_s1a_tops(self, date=None, mode=0, rshift_fromfile=None, ashift_fromfile=None):
        import os
        import subprocess

        if date is None or date == self.master:
            date = self.master
            # for master image mode should be 1
            mode = 1
        df = self.df.loc[[date]]
    
        xmlfile = os.path.relpath(df['metapath'][0], self.basedir)
        datafile = os.path.relpath(df['datapath'][0], self.basedir)
        #orbit = os.path.relpath(df['orbitfile'][0], self.basedir)
        stem = df['stem'][0]
    
        argv = ['make_s1a_tops', xmlfile, datafile, stem, str(mode)]
        if rshift_fromfile is not None:
            argv.append(rshift_fromfile)
        if ashift_fromfile is not None:
            argv.append(ashift_fromfile)
        #print ('argv', argv)
        p = subprocess.Popen(argv, stderr=subprocess.PIPE, cwd=self.basedir)
        stderr_data = p.communicate()[1]
        if len(stderr_data) > 0:
            print (stderr_data.decode('ascii'))
    
        self.ext_orb_s1a(stem, date)
    
        return

    def preproc(self, date=None, master=None, degrees=12.0/3600):
        import xarray as xr
        import numpy as np
        import os
        from PRM import PRM

        if date is None or date == self.master:
            # for master image
            master_line = list(self.get_master().itertuples())[0]
            #print (master_line)

            path_stem = os.path.join(self.basedir, master_line.stem)
            path_multistem = os.path.join(self.basedir, master_line.multistem)

            # generate prms and leds
            self.make_s1a_tops()

            PRM.from_file(path_stem + '.PRM')\
                .set(input_file = path_multistem + '.raw')\
                .update(path_multistem + '.PRM', safe=True)

            self.ext_orb_s1a(master_line.multistem)

            # recalculate after ext_orb_s1a
            earth_radius = PRM.from_file(path_multistem + '.PRM')\
                .calc_dop_orb(inplace=True).update().get('earth_radius')

            return PRM().set(earth_radius=earth_radius, stem=master_line.stem, multistem=master_line.multistem)
        else:
            # aligning for secondary image
            
            if not isinstance(master, PRM):
                raise Exception('Arguments master is not a PRM object')
            
            # prepare coarse DEM for alignment
            # 12 arc seconds resolution is enough, for SRTM 90m decimation is 4x4
            topo_llt = self.get_topo_llt(degrees=degrees)
            #topo_llt.shape

            line = list(self.get_aligned(date).itertuples())[0]
            print (line)
            
            # TODO: define 1st image for line, in the example we have no more
            tmp_da = 0
    
            # generate prms and leds
            self.make_s1a_tops(date)

            # compute the time difference between first frame and the rest frames
            t1, prf = PRM.from_file(f'raw/{line.stem}.PRM').get('clock_start', 'PRF')
            t2      = PRM.from_file(f'raw/{line.stem}.PRM').get('clock_start')
            nl = int((t2 - t1)*prf*86400.0+0.2)
            #echo "Shifting the master PRM by $nl lines..."

            # Shifting the master PRM by $nl lines...
            # shift the super-masters PRM based on $nl so SAT_llt2rat gives precise estimate
            prm1 = PRM.from_file(f'raw/{master.get("stem")}.PRM')
            prm1.set(prm1.sel('clock_start' ,'clock_stop', 'SC_clock_start', 'SC_clock_stop') + nl/prf/86400.0)
            tmp_prm = prm1
    
            # compute whether there are any image offset
            if tmp_da == 0:
                # tmp_prm defined above from {master}.PRM
                prm1 = tmp_prm.calc_dop_orb(master.get('earth_radius'), inplace=True)
                prm2 = PRM.from_file(f'raw/{line.stem}.PRM').calc_dop_orb(master.get('earth_radius'), inplace=True).update()
                lontie,lattie = prm1.SAT_baseline(prm2).get('lon_tie_point', 'lat_tie_point')
                tmp_am = prm1.SAT_llt2rat(coords=[lontie, lattie, 0], precise=1)[1]
                tmp_as = prm2.SAT_llt2rat(coords=[lontie, lattie, 0], precise=1)[1]
                # bursts look equal to rounded result int(np.round(...))
                tmp_da = int(tmp_as - tmp_am)
                print ('tmp_am', tmp_am, 'tmp_as', tmp_as, 'tmp_da', tmp_da)

            # in case the images are offset by more than a burst, shift the super-master's PRM again
            # so SAT_llt2rat gives precise estimate
            if abs(tmp_da) < 1000:
                # tmp.PRM defined above from {master}.PRM
                prm1 = tmp_prm.calc_dop_orb(master.get('earth_radius'), inplace=True)
                tmpm_dat = prm1.SAT_llt2rat(coords=topo_llt, precise=1)
                prm2 = PRM.from_file(f'raw/{line.stem}.PRM').calc_dop_orb(master.get('earth_radius'), inplace=True)
                tmp1_dat = prm2.SAT_llt2rat(coords=topo_llt, precise=1)
            else:
                raise Exception('TODO: Modifying master PRM by $tmp_da lines...')

            # echo get r, dr, a, da, SNR table to be used by fitoffset.csh
            offset_dat0 = np.hstack([tmpm_dat, tmp1_dat])
            func = lambda row: [row[0],row[5]-row[0],row[1],row[6]-row[1],100]
            offset_dat = np.apply_along_axis(func, 1, offset_dat0)

            # define radar coordinates extent
            rmax, amax = PRM.from_file(f'raw/{line.stem}.PRM').get('num_rng_bins','num_lines')
    
            # prepare the offset parameters for the stitched image
            # set the exact borders in radar coordinates
            par_tmp = offset_dat[(offset_dat[:,0]>0) & (offset_dat[:,0]<rmax) & (offset_dat[:,2]>0) & (offset_dat[:,2]<amax)]
            par_tmp[:,2] += nl
            if abs(tmp_da) >= 1000:
                par_tmp[:,2] -= tmp_da
                par_tmp[:,3] += tmp_da

            # prepare the rshift and ashift look up table to be used by make_s1a_tops
            # use tmp_dat instead of offset_dat
            r_xyz = offset_dat[:,[0,2,1]]
            a_xyz = offset_dat[:,[0,2,3]]

            r_grd = self.offset2shift(r_xyz, rmax, amax)
            r_grd.to_netcdf(f'raw/{line.stem}_r.grd')
    
            a_grd = self.offset2shift(a_xyz, rmax, amax)
            a_grd.to_netcdf(f'raw/{line.stem}_a.grd')
    
            # generate the image with point-by-point shifts
            # note: it removes calc_dop_orb parameters from PRM file
            self.make_s1a_tops(date=line.Index, mode=1,
                               rshift_fromfile=f'{line.stem}_r.grd',
                               ashift_fromfile=f'{line.stem}_a.grd')

            # need to update shift parameter so stitch_tops will know how to stitch
            PRM.from_file(f'raw/{line.stem}.PRM').set(PRM.fitoffset(3, 3, offset_dat)).update()

            # echo stitch images together and get the precise orbit
            # use stitch_tops tmp.stitchlist $stem to merge images

            # the raw file does not exist but it works
            PRM.from_file(f'raw/{line.stem}.PRM')\
                .set(input_file = f'{line.multistem}.raw')\
                .update(f'raw/{line.multistem}.PRM', safe=True)

            self.ext_orb_s1a(line.multistem, date=line.Index, )

            # Restoring $tmp_da lines shift to the image... 
            PRM.from_file(f'raw/{line.multistem}.PRM').set(ashift=0 if abs(tmp_da) < 1000 else tmp_da, rshift=0).update()

            # that is safe to rewrite source files
            prm1 = PRM.from_file(f'raw/{master.get("multistem")}.PRM')
            prm1.resamp(PRM.from_file(f'raw/{line.multistem}.PRM'),
                        alignedSLC_tofile=f'raw/{line.multistem}.SLC',
                        interp=1
            ).to_file(f'raw/{line.multistem}.PRM')

            PRM.from_file(f'raw/{line.multistem}.PRM').set(PRM.fitoffset(3, 3, par_tmp)).update()

            PRM.from_file(f'raw/{line.multistem}.PRM').calc_dop_orb(master.get('earth_radius'), 0, inplace=True).update()

    def intf(self, date1, date2, wavelength=400, psize=32):
        import os
        from PRM import PRM
    
        line1 = self.get_aligned(date1)
        filename1 = os.path.join(self.basedir, line1.multistem[0]+'.PRM')
        line2 = self.get_aligned(date2)
        filename2 = os.path.join(self.basedir, line2.multistem[0]+'.PRM')
    
        prm_ref = PRM.from_file(filename1)
        prm_rep = PRM.from_file(filename2)

        basename = prm_ref.intf(prm_rep, basedir=self.basedir, wavelength=wavelength, psize=psize)
        return basename

    def baseline_table(self, days, meters):
        return

#filelist = SBAS('raw_orig').set_master(MASTER)
#filelist.df
#filelist.get_master()
#filelist.get_aligned()
#filelist.to_file('raw/data.in.new')