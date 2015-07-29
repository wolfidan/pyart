"""
pyart.graph.radardisplay_airborne
=================================

Class for creating plots from Airborne Radar objects.

.. autosummary::
    :toctree: generated/
    :template: dev_template.rst

    RadarDisplay_Airborne

"""

import matplotlib.pyplot as plt
import numpy as np
import netCDF4
from mpl_toolkits.axes_grid1 import make_axes_locatable

from .radardisplay import RadarDisplay
from .common import (
    corner_to_point, radar_coords_to_cart, set_limits,
    generate_filename, generate_title, generate_vpt_title, generate_ray_title,
    generate_colorbar_label, parse_ax_fig, parse_ax, parse_vmin_vmax
    )
from .coord_transform import radar_coords_to_cart_track_relative
from .coord_transform import radar_coords_to_cart_earth_relative


class RadarDisplay_Airborne(RadarDisplay):
    """
    A display object for creating plots from data in a airborne radar object.

    Parameters
    ----------
    radar : Radar
        Radar object to use for creating plots, should be an airborne radar.
    shift : (float, float)
        Shifts in km to offset the calculated x and y locations.

    Attributes
    ----------
    plots : list
        List of plots created.
    plot_vars : list
        List of fields plotted, order matches plot list.
    cbs : list
        List of colorbars created.
    radar_name : str
        Name of radar.
    origin : str
        'Origin' or 'Radar'.
    shift : (float, float)
        Shift in meters.
    x, y, z : array
        Cartesian location of a sweep in meters.
    loc : (float, float)
        Latitude and Longitude of radar in degrees.
    time_begin : datetime
        Beginning time of first radar scan.
    starts : array
        Starting ray index for each sweep.
    ends : array
        Ending ray index for each sweep.
    fields : dict
        Radar fields.
    scan_type : str
        Scan type.
    ranges : array
        Gate ranges in meters.
    azimuths : array
        Azimuth angle in degrees.
    elevations : array
        Elevations in degrees.
    fixed_angle : array
        Scan angle in degrees.
    rotation : array
        Rotation angle in degrees.
    roll : array
        Roll angle in degrees.
    drift : array
        Drift angle in degrees.
    tilt : array
        Tilt angle in degrees.
    heading : array
        Heading angle in degrees.
    pitch : array
        Pitch angle in degrees.
    altitude : array
        Altitude angle in meters.


    """

    def __init__(self, radar, shift=(0.0, 0.0)):
        """ Initialize the object. """
        self.fixed_angle = radar.fixed_angle['data'][0]
        self.rotation = radar.rotation['data']
        self.roll = radar.roll['data']
        self.drift = radar.drift['data']
        self.tilt = radar.tilt['data']
        self.heading = radar.heading['data']
        self.pitch = radar.pitch['data']
        self.altitude = radar.altitude['data']
        super(RadarDisplay, self).__init__(radar, shift)

    def _calculateLocalization(self, radar):
        """ Calculate self.x, self.y, self.z and self.loc. """
        # x, y, z attributes: cartesian location for a sweep in km.

        if radar.metadata['platform_type'] == 'aircraft_belly':
            rg, azg = np.meshgrid(self.ranges, self.azimuths)
            rg, eleg = np.meshgrid(self.ranges, self.elevations)
            self.x, self.y, self.z = radar_coords_to_cart(
                rg / 1000.0, azg, eleg)
            self.x = self.x + self.shift[0]
            self.y = self.y + self.shift[1]
        else:
            rg, rotg = np.meshgrid(self.ranges, self.rotation)
            rg, rollg = np.meshgrid(self.ranges, self.roll)
            rg, driftg = np.meshgrid(self.ranges, self.drift)
            rg, tiltg = np.meshgrid(self.ranges, self.tilt)
            rg, pitchg = np.meshgrid(self.ranges, self.pitch)
            self.x, self.y, self.z = radar_coords_to_cart_track_relative(
                rg / 1000.0, rotg, rollg, driftg, tiltg, pitchg)
            self.x = self.x + self.shift[0]
            self.y = self.y + self.shift[1]

        # radar location in latitude and longitude
        middle_lat = int(radar.latitude['data'].shape[0] / 2)
        middle_lon = int(radar.longitude['data'].shape[0] / 2)
        lat = float(radar.latitude['data'][middle_lat])
        lon = float(radar.longitude['data'][middle_lon])
        self.loc = (lat, lon)

    ####################
    # Plotting methods #
    ####################

    def plot(self, field, sweep=0, **kwargs):
        """
        Create a plot appropiate for the radar.

        This function calls the plotting function corresponding to
        the scan_type of the radar.  Additional keywords can be passed to
        customize the plot, see the appropiate plot function for the
        allowed keywords.

        Parameters
        ----------
        field : str
            Field to plot.
        sweep : int
            Sweep number to plot, not used for VPT scans.

        See Also
        --------
        plot_ppi : Plot a PPI scan
        plot_sweep_grid : Plot a RHI or VPT scan

        """
        if self.scan_type == 'ppi':
            self.plot_ppi(field, sweep, **kwargs)
        elif self.scan_type == 'rhi':
            self.plot_sweep_grid(field, sweep, **kwargs)
        elif self.scan_type == 'vpt':
            self.plot_sweep_grid(field, sweep, **kwargs)
        else:
            raise ValueError('unknown scan_type % s' % (self.scan_type))
        return

    def plot_sweep_grid(self, field, sweep=0, mask_tuple=None, vmin=None, vmax=None,
                        cmap='jet', mask_outside=True, title=None,
                        title_flag=True, axislabels=(None, None),
                        axislabels_flag=True, colorbar_flag=True,
                        colorbar_label=None, colorbar_orient=None, edges=True,
                        filter_transitions=True, ax=None, fig=None):
        """
        Plot a sweep as a grid.

        Parameters
        ----------
        field : str
            Field to plot.
        sweep : int, optional
            Sweep number to plot.

        Other Parameters
        ----------------
        mask_tuple : (str, float)
            Tuple containing the field name and value below which to mask
            field prior to plotting, for example to mask all data where
            NCP < 0.5 set mask_tuple to ['NCP', 0.5]. None performs no masking.
        vmin : float
            Luminance minimum value, None for default value.
        vmax : float
            Luminance maximum value, None for default value.
        cmap : str
            Matplotlib colormap name.
        mask_outside : bool
            True to mask data outside of vmin, vmax.  False performs no
            masking.
        title : str
            Title to label plot with, None to use default title generated from
            the field and sweep parameters. Parameter is ignored if title_flag
            is False.
        title_flag : bool
            True to add a title to the plot, False does not add a title.
        axislabels : (str, str)
            2-tuple of x-axis, y-axis labels.  None for either label will use
            the default axis label.  Parameter is ignored if axislabels_flag is
            False.
        axislabel_flag : bool
            True to add label the axes, False does not label the axes.
        colorbar_flag : bool
            True to add a colorbar with label to the axis.  False leaves off
            the colorbar.
        colorbar_label : str
            Colorbar label, None will use a default label generated from the
            field information.
        colorbar_orient : str
            Colorbar orientation, None will use default orientation of
            vertical.
        edges : bool
            True will interpolate and extrapolate the gate edges from the
            range, azimuth and elevations in the radar, treating these
            as specifying the center of each gate.  False treats these
            coordinates themselved as the gate edges, resulting in a plot
            in which the last gate in each ray and the entire last ray are not
            plotted.
        filter_transitions : bool
            True to remove rays where the antenna was in transition between
            sweeps from the plot.  False will include these rays in the plot.
            No rays are filtered when the antenna_transition attribute of the
            underlying radar is not present.
        ax : Axis
            Axis to plot on. None will use the current axis.
        fig : Figure
            Figure to add the colorbar to. None will use the current figure.

        """
        # parse parameters
        ax, fig = parse_ax_fig(ax, fig)
        vmin, vmax = parse_vmin_vmax(self._radar, field, vmin, vmax)

        # get data for the plot
        data = self._get_data(field, sweep, mask_tuple, filter_transitions)
        x, z = self._get_x_z(field, sweep, edges, filter_transitions)

        # mask the data where outside the limits
        if mask_outside:
            data = np.ma.masked_invalid(data)
            data = np.ma.masked_outside(data, vmin, vmax)

        # plot the data
        pm = ax.pcolormesh(x, z, data, vmin=vmin, vmax=vmax, cmap=cmap)

        # Set the aspcet ratio
        # ax.axis('scaled')

        if title_flag:
            self._set_title(field, sweep, title, ax)

        if axislabels_flag:
            self._label_axes_ppi(axislabels, ax)

        # add plot and field to lists
        self.plots.append(pm)
        self.plot_vars.append(field)

        # colorbar options
        if colorbar_flag:
            self.plot_colorbar(mappable=pm, label=colorbar_label,
                               orient=colorbar_orient,
                               field=field, ax=ax, fig=fig)

    def label_xaxis_x(self, ax=None):
        """ Label the xaxis with the default label for x units. """
        ax = parse_ax(ax)
        ax.set_xlabel('Horizontal distance from ' + self.origin + ' (km)')

    def label_yaxis_y(self, ax=None):
        """ Label the yaxis with the default label for y units. """
        ax = parse_ax(ax)
        ax.set_ylabel('Horizontal distance from ' + self.origin + ' (km)')

    def label_yaxis_z(self, ax=None):
        """ Label the yaxis with the default label for y units. """
        ax = parse_ax(ax)
        ax.set_ylabel('Altitude (km)')
