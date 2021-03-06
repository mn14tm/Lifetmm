"""
Transfer matrix model for light inside a multilayer dielectric structure.

[1] Modeling photocurrent action spectra of photovoltaic devices based on organic thin films, Pettersson
[2] Principles of Nano-Optics, L. Novotny, B. Hecht
"""

import logging
import time

import matplotlib.pyplot as plt
import numpy as np
from numpy import pi, sqrt, sin, exp
from scipy.constants import c

from lifetmm.HelperFunctions import roots, snell, det

log = logging.getLogger(__name__)


class TransferMatrix:
    def __init__(self):
        # Structure parameters
        self.d_list = np.array([], dtype=float)
        self.n_list = np.array([], dtype=complex)
        self.d_cumulative = np.array([], dtype=float)
        self.num_layers = 0
        # Light parameters
        self.lam_vac = np.nan
        self.k_vac = np.nan
        self.omega = np.nan
        self.field = 'E'
        self.pol = 'TE'
        self.th = 0  # Angle of incidence from normal to multilayer [Leaky modes only]
        self.n_11 = 0  # Normalised parallel wave vector (or n_eff as used with guided modes )

    def add_layer(self, d, n):
        """
        Add layer of thickness d and refractive index n to the structure.
        Ensure that dimensions are consistent with layer thicknesses.
        """
        assert isinstance(d, (int, float)) or np.isreal(d), \
            ValueError('Thickness d must be either an integer or a float.')
        assert d >= 0, ValueError('Thickness must >= 0.')
        assert isinstance(n, (int, float, complex)), \
            ValueError('Refractive index n must be either an integer, float or complex number.')
        if self.num_layers == 0:
            assert np.isreal(n), ValueError('Incomming medium must be transparent (n is real).')
        self.d_list = np.append(self.d_list, d)
        self.n_list = np.append(self.n_list, n)
        # Recalculate structure info
        self.d_cumulative = np.cumsum(self.d_list)
        self.num_layers = np.size(self.d_list)

    def set_vacuum_wavelength(self, lam_vac):
        """
        Set the vacuum wavelength to be simulated.
        Ensure that dimensions are consistent with layer thicknesses.
        Only run this function after the structure has been defined.
        """
        assert isinstance(lam_vac, (int, float, complex)), \
            ValueError('This function is not vectorized; you need to run one calculation for each wavelength at a time')
        assert lam_vac > 0, ValueError('Wavelength must > 0.')
        assert self.num_layers > 0, ValueError('Define the structure first before using this function.')
        logging.debug('Lam_vac = %d nm', lam_vac)
        self.lam_vac = lam_vac
        self.k_vac = 2 * pi / lam_vac
        self.omega = c * self.k_vac

    def set_polarization(self, pol):
        """
        Set the mode polarisation to be simulated ('s' or 'TE' and 'p' or 'TM')
        """
        assert pol in ['s', 'p', 'TE', 'TM'], ValueError("Polarisation must one of; 's', 'p', 'TE', 'TM'")
        self.pol = pol

    def set_field(self, field):
        """
        Set the field to be evaluated. Either 'E' (default) or 'H' field.
        """
        assert field in ['E', 'H'], ValueError("The field must be either 'E' of 'H'.")
        self.field = field

    def set_incident_angle(self, th, units='radians'):
        """
        Set the incident angle of the plane wave (for a leaky mode). 0 deg is normal to the interface.
        """
        if hasattr(th, 'size') and th.size > 1:
            raise ValueError('This function is not vectorized; you need to run one '
                             'calculation for each angle at a time')
        if units == 'radians':
            assert 0 <= th < pi / 2, 'The light is not incident on the structure. ' \
                                     'Check input theta satisfies -pi/2 <= theta < pi/2'
            self.th = th
        elif units == 'degrees':
            assert 0 <= th < 90, 'The light is not incident on the structure. ' \
                                 'Check input theta satisfies -90 <= theta < 90'
            self.th = th * (pi / 180)
        else:
            raise ValueError('Units of angle not recognised. Please enter \'radians\' or \'degrees\'.')
        # Parallel normalised wave vector (continuous through interfaces)
        self.n_11 = self.n_list[0] * sin(self.th)

    def set_mode_n_11(self, n_11):
        """
        Set the normalised parallel wave vector, n_11=k_11/k_0 (for a guided mode where AOI is complex).
        """
        assert not isinstance(n_11, (list, np.ndarray)), ValueError('n_11 must be a number and not array/list.')
        self.n_11 = n_11

    def calc_xi(self, j):
        """
        Normalised perpendicular wave-vector in layer j. (q_j in Eq4 in [1]). 
        Note: Can be complex for use in fresnel equations when calculating interference matrix (metal layers).
        """
        nj = self.n_list[j]  # Normalised (complex) layer wave-vector magnitude (k(j)/k_vac)
        return sqrt(nj ** 2 - self.n_11 ** 2)

    def calc_k(self, j):
        """
        Calculate the wave vector magnitude (|k| = omega n / c) in layer j.
        """
        assert 0 <= j <= self.num_layers - 1, ValueError('j must be between 0 and num_layers-1.')
        assert not np.isnan(self.k_vac), ValueError('Wavevector not defined. Please set the vacuum wavelength.')
        return self.n_list[j].real * self.k_vac

    def calc_q(self, j):
        """
        Perpendicular wave vector in layer j.
        """
        assert not np.isnan(self.k_vac), ValueError('Wavevector not defined. Please set the vacuum wavelength.')
        xi = self.calc_xi(j)
        return xi * self.k_vac

    def calc_k_11(self):
        """
        Parallel wave vector (same in all layers).
        """
        assert not np.isnan(self.k_vac), ValueError('Wavevector not defined. Please set the vacuum wavelength.')
        return self.n_11 * self.k_vac

    def calc_wave_vector_components(self, j):
        """
        The wave vector magnitude and it's components perpendicular and parallel
        to the interface inside the layer j.
        """
        k = self.calc_k(j)
        k_11 = self.calc_k_11()
        q = self.calc_q(j)
        return k, q, k_11

    def i_matrix(self, j, k):
        """
        Returns the interference matrix between layers j and k.
        """
        nj = self.n_list[j]
        nk = self.n_list[k]
        qj = self.calc_xi(j)  # Using q notation instead of xi to match eq 3a and 3b in [1]
        qk = self.calc_xi(k)  # Ditto
        # Evaluate reflection and transmission coefficients for E field - ok for complex index of refraction [1]
        if self.pol in ['p', 'TM']:
            # Note r_p is defined where the E field flips direction by pi on reflection. See Fig 2.2 in [2].
            r = (nk ** 2 * qj - nj ** 2 * qk) / (nk ** 2 * qj + nj ** 2 * qk)
            t = (2 * nj * nk * qj) / (qj * nk ** 2 + qk * nj ** 2)
        elif self.pol in ['s', 'TE']:
            r = (qj - qk) / (qj + qk)
            t = (2 * qj) / (qj + qk)
        else:
            raise ValueError('A polarisation for the field must be set.')
        if self.field == 'H':
            # Convert transmission coefficient for E field to that of the H field.
            # The reflection coefficient is the same as the medium does not change.
            t *= nk / nj
        if t == 0:
            logging.debug('Transmission of i_matrix = 0. Returning inf.')
            return np.array([[np.inf, np.inf], [np.inf, np.inf]], dtype=complex)
        else:
            return (1 / t) * np.array([[1, r], [r, 1]], dtype=complex)

    def l_matrix(self, j):
        """
        Returns the propagation L matrix for layer j.
        """
        qj = self.calc_q(j)
        dj = self.d_list[j]
        assert dj > 0, ValueError('Layer {} does not have a thickness.'.format(j))
        assert exp(-1j * qj * dj) < np.finfo(np.complex).max, ValueError('l_matrix is unstable.')
        return np.array([[exp(-1j * qj * dj), 0], [0, exp(1j * qj * dj)]], dtype=complex)

    def s_matrix(self):
        """
        Returns the total system transfer matrix s.
        """
        s = self.i_matrix(0, 1)
        for j in range(1, self.num_layers - 1):
            l = self.l_matrix(j)
            i = self.i_matrix(j, j + 1)
            s = s @ l @ i
        return s

    def s_primed_matrix(self, layer):
        """
        Returns the partial system transfer matrix s_prime.
        """
        s_prime = self.i_matrix(0, 1)
        for j in range(1, layer):
            l = self.l_matrix(j)
            i = self.i_matrix(j, j + 1)
            s_prime = s_prime @ l @ i
        return s_prime

    def s_dprimed_matrix(self, layer):
        """
        Returns the partial system transfer matrix s_dprime (doubled prime).
        """
        s_dprime = self.i_matrix(layer, layer + 1)
        for j in range(layer + 1, self.num_layers - 1):
            l = self.l_matrix(j)
            i = self.i_matrix(j, j + 1)
            s_dprime = s_dprime @ l @ i
        return s_dprime

    def layer_field_amplitudes(self, layer):
        """
        Evaluate fwd and bkwd field amplitude coefficients (E or H) in a layer.
        Coefficients are in units of the fwd incoming wave amplitude for leaky modes
        and in terms of the superstrate (j=0) outgoing wave amplitude for guided modes.
        """
        n = self.n_list.real
        if self.n_11 < max(n[0], n[-1]):  # Mode is radiative
            # Calculate leaky amplitudes
            s = self.s_matrix()
            # Reflection for incoming wave incident of LHS of structure
            r = s[1, 0] / s[0, 0]
            if layer == 0:
                field_plus = 1 + 0j
                field_minus = r
            elif layer == self.num_layers - 1:
                field_plus = 1 / s[0, 0]
                field_minus = 0 + 0j
            else:
                q = self.calc_q(layer)
                d = self.d_list[layer]

                s_prime = self.s_primed_matrix(layer)
                s_dprime = self.s_dprimed_matrix(layer)
                t_prime = 1 / s_prime[0, 0]
                r_prime_minus = -s_prime[0, 1] / s_prime[0, 0]
                r_dprime = s_dprime[1, 0] / s_dprime[0, 0]

                field_plus = t_prime / (1 - r_prime_minus * r_dprime * exp(1j * 2 * q * d))
                field_minus = field_plus * r_dprime * exp(1j * 2 * q * d)
        else:  # Calculate guided amplitudes (2 outgoing waves no incoming)
            if layer == 0:
                field_plus = 0 + 0j
                field_minus = 1 + 0j
            elif layer == self.num_layers - 1:
                s = self.s_matrix()
                field_plus = 1 / s[1, 0]
                field_minus = 0 + 0j
            else:
                s_prime = self.s_primed_matrix(layer)
                assert not np.isclose(det(s_prime), 0), ValueError('Det=0 will give inf for field coefficient.')
                field_plus = - s_prime[0, 1] / det(s_prime)
                field_minus = s_prime[0, 0] / det(s_prime)
        return field_plus, field_minus

    def calc_layer_field(self, layer, z_step=1):
        """
        Evaluate the field (E or H) as a function of z (depth) into the layer, j.
        field_plus is the forward component of the field (e.g. E_j^+)
        field_minus is the backward component of the field (e.g. E_j^-)
        """
        assert self.d_list[layer] > 0, ValueError('Layer must have a thickness to use this function.')

        # Wave vector components in layer
        k, q, k_11 = self.calc_wave_vector_components(layer)

        # z positions to evaluate field at at
        z = np.arange((z_step / 2.0), self.d_list[layer], z_step)
        # Note field_plus and field_minus are defined at cladding-layer boundary so need to
        # propagate wave 'backwards' in the lower cladding by reversing z
        if layer == 0:
            z = -z[::-1]

        # field(z) field in terms of incident field amplitude
        field_plus, field_minus = self.layer_field_amplitudes(layer)
        field = field_plus * exp(1j * q * z) + field_minus * exp(-1j * q * z)
        field_squared = abs(field) ** 2

        # average value of the field_squared
        field_avg = sum(field_squared) / (z_step * self.d_list[layer])

        return {'z': z, 'field': field, 'field_squared': field_squared, 'field_avg': field_avg}

    def calc_field_structure(self, z_step=1):
        """
        Evaluate the field at all z positions within the structure.
        """
        z = np.arange((z_step / 2.0), self.d_cumulative[-1], z_step)
        # get z_mat - specifies what layer the corresponding point in z is in
        comp1 = np.kron(np.ones((self.num_layers, 1)), z)
        comp2 = np.transpose(np.kron(np.ones((len(z), 1)), self.d_cumulative))
        z_mat = sum(comp1 > comp2, 0)

        field = np.zeros(len(z), dtype=complex)
        # Loop through all layers with a thickness (claddings with 0 thickness will not show in z_mat)
        for layer in range(min(z_mat), max(z_mat) + 1):
            # logging.info simulation information to command line
            if layer == 0:
                logging.info('\tLayer -> lower cladding...')
            elif layer == self.num_layers - 1:
                logging.info('\tLayer -> upper cladding...')
            else:
                logging.info('\tLayer -> internal {0:d} / {1:d}...'.format(layer, self.num_layers - 2))
            time.sleep(0.2)  # Fixes progress bar occurring before text

            # Calculate z indices inside structure for the layer
            z_indices = np.where(z_mat == layer)
            field[z_indices] = self.calc_layer_field(layer)['field']
        field_squared = abs(field) ** 2
        return {'z': z, 'field': field, 'field_squared': field_squared}

    def get_layer_position_indices(self, layer, z_step=1):
        """Return z array indices for a chosen layer."""
        z = np.arange((z_step / 2.0), self.d_cumulative[-1], z_step)
        # get z_mat - specifies what layer the corresponding point in z is in
        comp1 = np.kron(np.ones((self.num_layers, 1)), z)
        comp2 = np.transpose(np.kron(np.ones((len(z), 1)), self.d_cumulative))
        z_mat = sum(comp1 > comp2, 0)
        return np.where(z_mat == layer)

    def calc_s11(self, n_11):
        """Return s_11 of s-matrix for a given n_11."""
        self.n_11 = n_11
        s = self.s_matrix()
        return s[0, 0].real

    def calc_guided_modes(self, verbose=True, normalised=False):
        """
        Return the parallel wave vectors (k_11 or beta) of all guided modes that the structure
        supports. Array returned is arranged from lowest mode to highest mode.

        If normalised=True return (k_ll/k_vac = n_11)

        Method: Evaluates the poles of the transfer matrix (S_11=0) as a function of n_11 in the
        guided regime:  n_clad < k_ll/k < max(n), k_11/k = n_11
        """
        n = self.n_list.real
        assert self.supports_guiding(), ValueError('This structure does not support wave guiding.')
        # Find supported guiding modes - max(n_clad) > n_11 >= max(n)
        n_11 = roots(self.calc_s11, 1 * max(n[0], n[-1]), max(n), verbose=verbose)
        # Flip array to arrange from lowest to highest mode (highest to lowest n_11)
        n_11 = n_11[::-1]

        ind = np.where(n_11 - min(n) < 0.01)
        n_11 = np.delete(n_11, ind)

        if normalised:
            return n_11
        else:
            return n_11 * self.k_vac

    def calc_group_velocity(self):
        """
        Calculate the group velocity of the structure at lam_vac for guided modes.
        """
        lam_vac = self.lam_vac

        # Take lambda+-1 either side of the emission wavelength
        self.set_vacuum_wavelength(int(1 + lam_vac))
        omega1 = self.omega
        beta_lower = self.calc_guided_modes(verbose=False, normalised=False)

        self.set_vacuum_wavelength(int(-1 + lam_vac))
        omega2 = self.omega
        beta_upper = self.calc_guided_modes(verbose=False, normalised=False)

        assert len(beta_lower) == len(beta_upper), \
            ValueError('Number of guided modes must be equal when calculating the group velocity.')

        d_beta = beta_upper - beta_lower
        d_omega = omega2 - omega1
        vg = d_omega / d_beta
        logging.debug(vg)
        # Reset the vacuum emission wavelength to start of function
        self.set_vacuum_wavelength(lam_vac)
        return vg

    def get_layer_boundaries(self):
        """
        Return layer boundary zs assuming that the lower cladding boundary is at z=0.
        """
        return self.d_cumulative

    def get_structure_thickness(self):
        """
        Return the structure thickness.
        """
        return self.d_cumulative[-1]

    def calc_z_to_lambda(self, z, center=True):
        """
        Convert z positions to units of wavelength (optional) from the centre.
        """
        if center:
            z -= self.get_structure_thickness() / 2
        z /= self.lam_vac
        return z

    def calc_r_and_t(self):
        """
        Return the complex reflection and transmission coefficients of the structure.
        """
        s = self.s_matrix()
        r = s[1, 0] / s[0, 0]
        t = 1 / s[0, 0]
        return r, t

    def calc_reflectance_and_transmittance(self, correction=True):
        """
        Return the reflectance and transmittance of the structure.
        Correction option for transmission due to beam expansion:
            https://en.wikipedia.org/wiki/Fresnel_equations
        """
        r, t = self.calc_r_and_t()
        reflectance = abs(r) ** 2
        transmittance = abs(t) ** 2
        if correction:
            n_1 = self.n_list[0].real
            n_2 = self.n_list[-1].real
            th_out = snell(n_1, n_2, self.th)
            rho = n_2 / n_1
            m = np.cos(th_out) / np.cos(self.th)
            transmittance *= rho * m
        return reflectance, transmittance

    def calc_reflectivity_vs_angle(self, th_lower=0, th_upper=90, num=1E4, plot=True):
        """ Reflection vs AOI"""
        th_init = self.th
        th_list = np.linspace(th_lower, th_upper, num, endpoint=False)
        rs_list = []
        rp_list = []
        for theta in th_list:
            self.set_incident_angle(theta, units='degrees')
            self.set_polarization('s')
            rs, t = self.calc_r_and_t()
            rs_list.append(rs)
            self.set_polarization('p')
            rp, t = self.calc_r_and_t()
            rp_list.append(rp)
        rs_list = np.array(rs_list)
        rp_list = np.array(rp_list)

        if plot:
            fig, (ax1, ax2) = plt.subplots(2, sharex='row')
            ax1.set_ylabel(r'Reflection ($|r|^2)$')
            ax1.plot(th_list, abs(rs_list) ** 2, '--', label='s')
            ax1.plot(th_list, abs(rp_list) ** 2, label='p')
            ax1.plot(th_list, (abs(rs_list) ** 2 + abs(rp_list) ** 2) / 2, label='Unpolarised')
            ax2.set_ylabel('Reflection phase (deg)')
            ax2.plot(th_list, np.angle(rs_list, deg=True), '--', label='s')
            # Note r_p is defined where the E field flips on reflection [2] pg.22
            # therefore we multiply by e^(i*pi) to shift by 180 degrees so that a
            # negative angle implies a flipped E field
            ax2.plot(th_list, np.angle(-1 * rp_list, deg=True), label='p')
            ax2.set_xlabel('AOI (degrees)')
            ax1.legend()
            ax2.legend()
            plt.show()
            self.set_incident_angle(th_init, units='degrees')
            return {'th_list': th_list, 'rs_list': rs_list, 'rp_list': rp_list, 'fig': fig}
        else:
            return {'th_list': th_list, 'rs_list': rs_list, 'rp_list': rp_list}

    def calc_transmission_vs_angle(self, th_lower=0, th_upper=90, num=1E4, plot=True):
        """
        Dependence of the power reflectivity and phase on the angle of incidence.
        Light incident from medium of refractive index n1 to medium of refractive index n2
        """
        th_list = np.linspace(th_lower, th_upper, num, endpoint=False)
        ts_list = []
        tp_list = []
        for theta in th_list:
            self.set_incident_angle(theta, units='degrees')
            self.set_polarization('s')
            rs, ts = self.calc_r_and_t()
            ts_list.append(ts)
            self.set_polarization('p')
            rp, tp = self.calc_r_and_t()
            tp_list.append(tp)
        ts_list = np.array(ts_list)
        tp_list = np.array(tp_list)

        if plot:
            fig, (ax1, ax2) = plt.subplots(2, sharex='row')
            ax1.set_ylabel(r'Transmission ($|t|^2)$')
            ax1.plot(th_list, abs(ts_list) ** 2, '--', label='s')
            ax1.plot(th_list, abs(tp_list) ** 2, label='p')
            ax1.plot(th_list, (abs(ts_list) ** 2 + abs(tp_list) ** 2) / 2, label='Unpolarised')
            ax2.set_ylabel('Transmitted phase (deg)')
            ax2.plot(th_list, np.angle(ts_list, deg=True), '--', label='s')
            # Note r_p is defined where the E field flips on reflection [2] pg.22
            # therefore we multiply by e^(i*pi) to shift by 180 degrees so that a negative angle implies a flipped E field
            ax2.plot(th_list, np.angle(-1 * tp_list, deg=True), label='p')
            ax2.set_xlabel('AOI (degrees)')
            ax1.legend()
            ax2.legend()
            plt.show()
            return {'th_list': th_list, 'ts_list': ts_list, 'tp_list': tp_list, 'fig': fig}
        else:
            return {'th_list': th_list, 'ts_list': ts_list, 'tp_list': tp_list}

    def calc_reflectivity_vs_wavelength(self, lam_lower=500, lam_upper=1500, num=1000, plot=True):
        """ Reflection coefficient vs lam0"""

        lam_init = self.lam_vac
        lam_list = np.linspace(lam_lower, lam_upper, num, endpoint=True)
        rs_list = []
        rp_list = []
        for lam in lam_list:
            # Do calculations
            self.set_vacuum_wavelength(lam)
            self.set_polarization('s')
            r, t = self.calc_reflectance_and_transmittance(correction=False)
            rs_list.append(r)
            self.set_polarization('p')
            r, t = self.calc_reflectance_and_transmittance(correction=False)
            rp_list.append(r)

        if plot:
            fig, ax = plt.subplots()
            ax.plot(lam_list, rs_list, '--', label='s')
            ax.plot(lam_list, rp_list, label='p')
            ax.set_xlabel('Wavelength (nm)')
            ax.set_ylabel(r'Reflection ($|r|^2)$')
            plt.legend()
            plt.show()

        self.set_vacuum_wavelength(lam_init)
        return lam_list, rs_list, rp_list

    def calc_absorption(self):
        n = self.n_list
        # Absorption coefficient in 1/cm
        absorption = np.zeros(self.num_layers)
        for layer in range(1, self.num_layers):
            absorption[layer] = (4 * pi * n[layer].imag) / (self.lam_vac * 1.0e-7)
        return absorption

    def flip(self):
        """
        Flip the structure front-to-back.
        """
        self.d_list = self.d_list[::-1]
        self.n_list = self.n_list[::-1]
        self.d_cumulative = np.cumsum(self.d_list)
        logging.info('WARNING: Rerun set_incident_angle() function before doing the calculations to recalculate n_11.')

    def info(self):
        """
        Command line verbose feedback of the structure.
        """
        logging.info('****************************')
        logging.info('****** Simulation info *****\n')
        logging.info('Multi-layered Structure:')
        logging.info('    d\t\tn')
        for n, d in zip(self.n_list, self.d_list):
            logging.info('{0:5.4g}\t\t{1:4g}'.format(d, n))
        logging.info('\nFree space wavelength: {:g}'.format(self.lam_vac))
        logging.info('****************************\n')

    def show_structure(self):
        """
        Brings up a plot showing the structure.
        """
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        from collections import OrderedDict

        # Shades to fill rectangles with based on refractive index
        alphas = abs(self.n_list) / max(abs(self.n_list))

        fig, ax = plt.subplots()
        for i, dx in enumerate(self.d_list):
            if dx > 0:
                x = self.d_cumulative[i]
                layer_text = ('{0.real:.2f} + {0.imag:.2f}j'.format(self.n_list[i]))
                p = patches.Rectangle(
                    (x - dx, 0.0),  # (x,y)
                    dx,  # width
                    1.0,  # height
                    alpha=alphas[i],
                    linewidth=2,
                    label=layer_text,
                )
                ax.add_patch(p)
        # Create legend without duplicate keys
        handles, labels = ax.get_legend_handles_labels()
        by_label = OrderedDict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), title='n')
        ax.set_xlim([0, self.d_cumulative[-1]])
        ax.set(xlabel=r'x')
        ax.yaxis.set_visible(False)
        plt.show()

    def supports_guiding(self):
        n = self.n_list
        # Eq (11)
        if np.any(n[1:-1] > max(n[0], n[-1])):
            return True
        else:
            return False

    def mode_type(self):
        # See Quantum Electronics by Yariv pg.603
        n = self.n_list
        if len(n) > 2 and max(n[1:-1]) >= self.n_11 >= min(n[0], n[-1]):
            return 'Guided'
        else:
            return 'Leaky'
