"""
Recreate plots from

    'Measuring and modifying the spontaneous emission rate of erbium near an interface'
    by Snoeks, E, Lagendijk, A, Polman, A
"""

import matplotlib.pyplot as plt
import numpy as np
from scipy.constants import pi

from lifetmm.SPE import SPE


def fig3():
    """ Plot the average decay rate of layer(normalised to bulk n) vs n of semi-infinite
     half space.

     Note:
         * we use the spe_layer function as we only care about the Er-doped layer.
         * th_num option is specified to give a higher accuracy on the integration.
    """
    # Vacuum emission wavelength
    lam0 = 1550

    results = []
    n_list = np.linspace(1, 2, 10)
    for n in n_list:
        print('Evaluating n={:g}'.format(n))
        # Create structure
        st = SPE()
        st.add_layer(lam0, 1.5)
        st.add_layer(0, n)
        st.set_vacuum_wavelength(lam0)
        # Calculate average total spontaneous emission of layer 0 (1st)
        result = st.calc_spe_layer_leaky(layer=0, emission='Lower', th_pow=11)
        spe = result['spe']['total']
        result = st.calc_spe_layer_leaky(layer=0, emission='Upper', th_pow=11)
        spe += result['spe']['total']
        spe /= 2
        spe = np.mean(spe)
        # Normalise to bulk refractive index
        spe -= 1.5
        # Append to list
        results.append(spe)
    results = np.array(results)

    # Plot results
    f, ax = plt.subplots(figsize=(15, 7))
    ax.plot(n_list, results)
    ax.set_title('Average spontaneous emission rate over doped layer (d=1550nm) '
                 'normalised to emission rate in bulk medium.')
    ax.set_ylabel('$\Gamma / \Gamma_1.5$')
    ax.set_xlabel('n')
    plt.tight_layout()
    if SAVE:
        plt.savefig('../Images/spe_vs_n.png', dpi=300)
        np.savez('../Data/spe_vs_n', n=n_list, spe=results)
    plt.show()


def fig4():
    """ n=3 or n=1 (air) to n=1.5 (Erbium deposition) semi-infinite half spaces.
    Plot the average total spontaneous emission rate of dipoles as a function of
    distance from the interface.
    """
    # Vacuum wavelength
    lam0 = 1550
    # Plotting units
    units = lam0 / (2 * pi)

    # Create plot
    f, ax = plt.subplots()

    for n in [1, 2]:
        print('Evaluating n={:g}'.format(n))
        # Create structure
        st = SPE()
        st.add_layer(4 * units, n)
        st.add_layer(4 * units, 1.5)
        st.set_vacuum_wavelength(lam0)
        st.info()
        # Calculate spontaneous emission over whole structure
        result = st.calc_spe_structure()
        z = result['z']
        # Shift so centre of structure at z=0
        z -= st.get_structure_thickness() / 2
        spe = result['leaky']['avg']
        # Plot spontaneous emission rates
        ax.plot(z/units, spe, label=('n='+str(n)), lw=2)
        ax.axhline(y=n, xmin=0, xmax=0.4, ls='dotted', color='k', lw=2)

        # Plot internal layer boundaries
        for z in st.get_layer_boundaries()[:-1]:
            # Shift so centre of structure at z=0
            z -= st.get_structure_thickness() / 2
            ax.axvline(z/units, color='k', lw=2)

    ax.axhline(1.5, ls='--', color='k', lw=2)
    ax.set_title('Spontaneous emission rate at boundary for semi-infinite media. RHS n=1.5.')
    ax.set_ylabel('$\Gamma / \Gamma_0$')
    ax.set_xlabel('Position z ($\lambda$/2$\pi$)')
    plt.legend(title='LHS n')
    plt.tight_layout()
    if SAVE:
        plt.savefig('../Images/spe_vs_n.png', dpi=300)
    plt.show()


if __name__ == "__main__":
    SAVE = False

    # fig3()
    # fig4()
