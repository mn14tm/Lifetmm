"""
Calculations to look at the SE rate in structures designed to reduce radiation trapping
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from lifetmm.SPE import SPE


def all_plots():
    """Plot SE rates for vertical and horizontal dipoles. Then plot sum for randomly orientated dipole."""

    import matplotlib as mpl
    mpl.rc('figure', dpi=250)

    # Create structure
    st = SPE()
    st.add_layer(2.5 * lam0, si)
    st.add_layer(100, edts)
    st.add_layer(2.5 * lam0, si)
    st.set_vacuum_wavelength(lam0)
    st.info()

    # Calculate
    res = st.calc_spe_structure(th_pow=11)
    z = res['z']
    z = st.calc_z_to_lambda(z)

    # ------- Plots -------
    # leaky modes plot
    spe = res['leaky']
    fig = plt.figure()
    ax1 = fig.add_subplot(211)
    ax1.plot(z, spe['TE'], label='TE')
    ax1.plot(z, spe['TM_p'], label='TM')
    ax1.plot(z, spe['TE'] + spe['TM_p'], 'k', label='TE + TM')
    ax2 = fig.add_subplot(212)
    ax2.plot(z, spe['TM_s'], label='TM')

    ax1.set_title('Spontaneous Emission Rate (leaky).')
    ax1.set_ylabel('$\Gamma / \Gamma_0$')
    ax2.set_ylabel('$\Gamma /\Gamma_0$')
    ax2.set_xlabel('z/$\lambda$')
    ax1.legend(title='Horizontal Dipoles', loc='lower right', fontsize='medium')
    ax2.legend(title='Vertical Dipoles', loc='lower right', fontsize='medium')

    # Draw rectangles for the refractive index and lines at boundaries
    for zb in st.get_layer_boundaries()[:-1]:
        zb = st.calc_z_to_lambda(zb)
        ax1.axvline(x=zb, color='k', lw=2)
        ax2.axvline(x=zb, color='k', lw=2)

    ax1b = ax1.twinx()
    ax2b = ax2.twinx()
    for z0, dz, n in zip(st.d_cumulative, st.d_list, st.n_list):
        z0 = st.calc_z_to_lambda(z0)
        dz = st.calc_z_to_lambda(dz, center=False)
        rect = Rectangle((z0 - dz, 0), dz, n.real, facecolor='c', alpha=0.2)
        ax1b.add_patch(rect)
        ax1b.set_ylabel('n')
        ax1b.set_ylim(ax1.get_ylim())
        rect = Rectangle((z0 - dz, 0), dz, n.real, facecolor='c', alpha=0.2)
        ax2b.add_patch(rect)
        ax2b.set_ylabel('n')
        ax2b.set_ylim(ax2.get_ylim())
    ax1.set_zorder(ax1b.get_zorder() + 1)  # put ax1 in front of ax2
    ax1.patch.set_visible(False)  # hide ax1'canvas'
    ax2.set_zorder(ax2b.get_zorder() + 1)  # put ax1 in front of ax2
    ax2.patch.set_visible(False)  # hide ax1'canvas'

    if SAVE:
        plt.savefig('../Images/leaky')
    # plt.show()

    # Guided modes plot
    if st.supports_guiding():
        spe = res['guided']
        fig = plt.figure()
        ax1 = fig.add_subplot(211)
        ax1.plot(z, spe['TE'], label='TE')
        ax1.plot(z, spe['TM_p'], label='TM')
        ax1.plot(z, spe['TE'] + spe['TM_p'], 'k', label='TE + TM')
        ax2 = fig.add_subplot(212)
        ax2.plot(z, spe['TM_s'], label='TM')

        ax1.set_title('Spontaneous Emission Rate (guided).')
        ax1.set_ylabel('$\Gamma / \Gamma_0$')
        ax2.set_ylabel('$\Gamma /\Gamma_0$')
        ax2.set_xlabel('z/$\lambda$')
        ax1.legend(title='Horizontal Dipoles', loc='lower right', fontsize='medium')
        ax2.legend(title='Vertical Dipoles', loc='lower right', fontsize='medium')

        # Draw rectangles for the refractive index and lines at boundaries
        for zb in st.get_layer_boundaries()[:-1]:
            zb = st.calc_z_to_lambda(zb)
            ax1.axvline(x=zb, color='k', lw=2)
            ax2.axvline(x=zb, color='k', lw=2)

        ax1b = ax1.twinx()
        ax2b = ax2.twinx()
        for z0, dz, n in zip(st.d_cumulative, st.d_list, st.n_list):
            z0 = st.calc_z_to_lambda(z0)
            dz = st.calc_z_to_lambda(dz, center=False)
            rect = Rectangle((z0 - dz, 0), dz, n.real, facecolor='c', alpha=0.2)
            ax1b.add_patch(rect)
            ax1b.set_ylabel('n')
            ax1b.set_ylim(ax1.get_ylim())
            rect = Rectangle((z0 - dz, 0), dz, n.real, facecolor='c', alpha=0.2)
            ax2b.add_patch(rect)
            ax2b.set_ylabel('n')
            ax2b.set_ylim(ax2.get_ylim())
        ax1.set_zorder(ax1b.get_zorder() + 1)  # put ax1 in front of ax2
        ax1.patch.set_visible(False)  # hide ax1'canvas'
        ax2.set_zorder(ax2b.get_zorder() + 1)  # put ax1 in front of ax2
        ax2.patch.set_visible(False)  # hide ax1'canvas'

        if SAVE:
            plt.savefig('../Images/guided')
            # plt.show()

    # parallel and perpendicular dipole orientation (leaky + guided)
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex='col', sharey='none')
    if st.supports_guiding():
        ax1.plot(z, res['leaky']['parallel'] + res['guided']['parallel'], label='h')
        ax2.plot(z, res['leaky']['perpendicular'] + res['guided']['perpendicular'], label='v')
    else:
        ax1.plot(z, res['leaky']['parallel'], label='h')
        ax2.plot(z, res['leaky']['perpendicular'], label='v')

    ax1.set_ylabel('$\Gamma / \Gamma_0$')
    ax2.set_ylabel('$\Gamma / \Gamma_0$')
    ax2.set_xlabel('Position z ($\lambda$)')
    ax1.set_title('Parallel/Horizontal')
    ax2.set_title('Perpendicular/Vertical')

    # Draw rectangles for the refractive index and lines at boundaries
    for zb in st.get_layer_boundaries()[:-1]:
        zb = st.calc_z_to_lambda(zb)
        ax1.axvline(x=zb, color='k', lw=2)
        ax2.axvline(x=zb, color='k', lw=2)

    ax1b = ax1.twinx()
    ax2b = ax2.twinx()
    for z0, dz, n in zip(st.d_cumulative, st.d_list, st.n_list):
        z0 = st.calc_z_to_lambda(z0)
        dz = st.calc_z_to_lambda(dz, center=False)
        rect = Rectangle((z0 - dz, 0), dz, n.real, facecolor='c', alpha=0.2)
        ax1b.add_patch(rect)
        ax1b.set_ylabel('n')
        ax1b.set_ylim(ax1.get_ylim())
        rect = Rectangle((z0 - dz, 0), dz, n.real, facecolor='c', alpha=0.2)
        ax2b.add_patch(rect)
        ax2b.set_ylabel('n')
        ax2b.set_ylim(ax2.get_ylim())
    ax1.set_zorder(ax1b.get_zorder() + 1)  # put ax1 in front of ax2
    ax1.patch.set_visible(False)  # hide ax1'canvas'
    ax2.set_zorder(ax2b.get_zorder() + 1)  # put ax1 in front of ax2
    ax2.patch.set_visible(False)  # hide ax1'canvas'

    if SAVE:
        plt.savefig('../Images/individual')
    # plt.show()

    # Average dipole orientation (leaky + guided)
    fig, ax1 = plt.subplots()
    if st.supports_guiding():
        ax1.plot(z, res['leaky']['avg'] + res['guided']['avg'], label='Avg')
    else:
        ax1.plot(z, res['leaky']['avg'], label='Avg')
    ax1.set_title('Average total SE rate.')
    ax1.set_ylabel('$\Gamma / \Gamma_0$')
    ax1.set_xlabel('Position z ($\lambda$)')
    ax1.legend()

    # Draw rectangles for the refractive index
    ax2 = ax1.twinx()
    for z0, dz, n in zip(st.d_cumulative, st.d_list, st.n_list):
        z0 = st.calc_z_to_lambda(z0)
        dz = st.calc_z_to_lambda(dz, center=False)
        rect = Rectangle((z0 - dz, 0), dz, n.real, facecolor='c', alpha=0.15)
        ax2.add_patch(rect)  # Note: add to ax1 so that zorder has effect
    ax2.set_ylabel('n')
    ax2.set_ylim(ax1.get_ylim())
    ax1.set_zorder(ax2.get_zorder() + 1)  # put ax1 in front of ax2
    ax1.patch.set_visible(False)  # hide ax1'canvas'

    # Draw layer boundaries
    for zb in st.get_layer_boundaries()[:-1]:
        zb = st.calc_z_to_lambda(zb)
        ax1.axvline(x=zb, color='k', lw=2)

    if SAVE:
        plt.savefig('../Images/total')
    plt.show()


if __name__ == "__main__":
    SAVE = True

    # Set vacuum wavelength
    lam0 = 1550

    # Material refractive index at lam0
    air = 1
    sio2 = 1.45
    edts = 1.6
    si = 3.48

    all_plots()
