#	$Id: Makefile 109 2015-01-19 23:01:24Z sandwell $
#
#	makefile for gmtsar directory (sbas.c not included yet)

include ../config.mk

INCLUDES	= $(GMT_INC) -I./ -I$(TIFF_INC)

LIB_C		= aastretch.c acpatch.c calc_dop.c conv2d.c do_freq_xcorr.c \
		  do_time_int_xcorr.c fft_bins.c fft_interpolate_routines.c \
		  file_stuff.c geoxyz.c get_locations.c get_params.c hermite_c.c \
		  highres_corr.c interpolate_orbit.c intp_coef.c ldr_orbit.c \
		  parse_xcorr_input.c plxyz.c polyfit.c print_results.c radopp.c \
		  read_orb.c read_xcorr_data.c SAT_llt2rat_sub.c \
		  rmpatch.c rng_cmp.c rng_ref.c set_prm_defaults.c shift.c \
		  sio_struct.c siocomplex.c spline.c trans_col.c utils.c utils_complex.c \
		  write_orb.c sbas_utils.c stringutils.c update_PRM_sub.c rng_filter.c \
		  lib_strfuncs.c

LIB_O		= $(LIB_C:.c=.o)
LIB		= libgmtsar.$(LIBEXT)

#-------------------------------------------------------------------------------
#	library
#-------------------------------------------------------------------------------

$(LIB):		$(LIB_O)
		$(AR) cvur $@ $?
		$(RANLIB) $@

lib:		$(LIB)

PROGS_C		= bperp.c calc_dop_orb.c conv.c esarp.c offset_topo.c phase2topo.c \
		  phasediff.c phasefilt.c resamp.c xcorr.c extend_orbit.c update_PRM.c get_PRM.c \
		  SAT_llt2rat.c SAT_look.c SAT_baseline.c make_gaussian_filter.c sbas.c \
          nearest_grid.c fitoffset.c solid_tide.c p_scatter.c split_spectrum.c cut_slc.c \
          split_aperture.c phasediff_get_topo_phase.c geocode_slc.c

PROGS_O         = $(PROGS_C:.c=.o)
PROGS           = $(PROGS_C:.c=)

#-------------------------------------------------------------------------------
#	software targets
#-------------------------------------------------------------------------------

all:		$(PROGS)

install:	all
		$(INSTALL) -d $(bindir)
		$(INSTALL) $(PROGS) $(bindir)
		ls csh/*.csh csh/*.sh csh/*.py py/*.py sh/*.sh > /tmp/t.lis
		$(INSTALL) `cat /tmp/t.lis` $(bindir)
		rm -f /tmp/t.lis

uninstall:
		cd $(bindir); rm -f $(PROGS)
		cd csh; ls *.csh *.sh *.py > /tmp/t.lis
		cd $(bindir); rm -f `cat /tmp/t.lis`
		rm -f /tmp/t.lis

spotless::	clean

clean:	
		rm -f *.a *.o *% core tags $(PROGS)

#-------------------------------------------------------------------------------
#	program rules
#-------------------------------------------------------------------------------

$(PROGS):	$(PROGS_O) $(LIB)
		$(CC) $(LDFLAGS) $@.o $(GMTSAR) $(GMT_LIB) $(LALIBS) $(LIBS)  -L$(TIFF_LIB) -ltiff -lm -o $@
