# coding: utf-8

"""
Some utils for trigger studies and efficiency calculations
"""

from __future__ import annotations

import law

from columnflow.util import maybe_import

logger = law.logger.get_logger(__name__)

hist = maybe_import("hist")
np = maybe_import("numpy")
scipy = maybe_import("scipy")
mpl = maybe_import("matplotlib")
plt = maybe_import("matplotlib.pyplot")
mplhep = maybe_import("mplhep")
ak = maybe_import("awkward")


def safe_div(num, den, default=1.0):
    """
    Safely divide two arrays, setting the result to:
    - num / den where num >= 0 and den > 0
    - 0 where num == 0 and den == 0
    - 1 where num >= 0 and den == 0
    at the moment not used
    """
    return np.where(
        (num == 0) & (den == 0),
        default,
        np.where(
            (num >= 0) & (den > 0),
            num / den,
            1.0
        )
    )


def binom_int(num, den, confint=0.68):
    """
    calculates clopper-pearson error
    """
    from scipy.stats import beta
    quant = (1 - confint) / 2.
    low = beta.ppf(quant, num, den - num + 1)
    high = beta.ppf(1 - quant, num + 1, den - num)
    return (np.nan_to_num(low), np.where(np.isnan(high), 1, high))


def calc_efficiency_errors(num, den):
    """
    Calculate the error on an efficiency given the numerator and denominator histograms.
    """

    # Use the variance to scale the numerator and denominator to remove an average weight,
    # this reduces the errors for rare processes to more realistic values
    num_scale = np.nan_to_num(num.values() / num.variances(), nan=1)
    den_scale = num_scale  # np.nan_to_num(den.values() / den.variances(), nan=1)

    efficiency = np.nan_to_num((num.values()*num_scale) / (den.values()*den_scale), nan=0, posinf=1, neginf=0)

    if np.any(efficiency > 1):
        logger.warning(
            "Some efficiencies for are greater than 1",
        )
    elif np.any(efficiency < 0):
        logger.warning(
            "Some efficiencies for are less than 0",
        )

    band_low, band_high = binom_int(num.values() * num_scale, den.values() * den_scale)

    error_low = np.asarray(efficiency - band_low)
    error_high = np.asarray(band_high - efficiency)

    # remove negative errors
    if np.any(error_low < 0):
        logger.warning("Some lower uncertainties are negative, setting them to zero")
        error_low[error_low < 0] = 0
    if np.any(error_high < 0):
        logger.warning("Some upper uncertainties are negative, setting them to zero")
        error_high[error_high < 0] = 0

    # remove large errors if the efficiency is zero
    error_low[efficiency == 0] = 0
    error_high[efficiency == 0] = 0

    # stacking errors
    errors = np.concatenate(
        (np.expand_dims(error_low, axis=1), np.expand_dims(error_high, axis=1)),
        axis=1,
    )
    # this works for 1D histograms but needs to be undone for 2d histograms, no idea why
    errors = errors.T

    return errors


def calc_sf_uncertainty(efficiencies: dict, errors: dict, alpha: np.ndarray):
    """
    Calculate the error on the scale factors using a gaussian error propagation.
    """
    # symmetrize errors
    sym_errors = {}
    for key, value in errors.items():
        if value.ndim == 2 and value.shape[0] == 2:
            sym_errors[key] = np.maximum(value[0], value[1])
        else:
            # here the transponse is undone again
            sym_errors[key] = np.maximum(value.T[..., 0, :], value.T[..., 1, :])

    # combine errors
    uncertainty = np.sqrt(
        (sym_errors[0] / efficiencies[1]) ** 2 + (efficiencies[0] * sym_errors[1] / efficiencies[1] ** 2) ** 2 # + (1 - alpha) ** 2  # noqa
    )

    return np.nan_to_num(uncertainty, nan=0, posinf=1, neginf=0)


def calculate_efficiencies(
        h: hist.Hist,
        trigger: str,
) -> dict:
    """
    Calculates the efficiencies for the different triggers.
    """
    efficiencies = {}
    efficiency_unc = {}
    # loop over processes
    for proc in range(h.axes[0].size):

        efficiency = np.nan_to_num(h[proc, ..., hist.loc(trigger)].values() / h[proc, ..., 0].values(),
                                   nan=0, posinf=1, neginf=0
                                   )

        if np.any(efficiency > 1):
            logger.warning(
                "Some efficiencies for are greater than 1, errorbars are capped at zero",
            )
        elif np.any(efficiency < 0):
            logger.warning(
                "Some efficiencies for are less than 0, errorbars are capped at zero",
            )

        efficiencies[proc] = efficiency

        efficiency_unc[proc] = calc_efficiency_errors(h[proc, ..., hist.loc(trigger)], h[proc, ..., 0])

    return efficiencies, efficiency_unc


def rebin_hist(h, axis_name, edges):
    if isinstance(edges, int):
        return h[{axis_name: hist.rebin(edges)}]

    ax = h.axes[axis_name]
    ax_idx = [a.name for a in h.axes].index(axis_name)
    if not all([np.isclose(x, ax.edges).any() for x in edges]):
        raise ValueError(
            f"Cannot rebin histogram due to incompatible edges for axis '{ax.name}'\n"
            f"Edges of histogram are {ax.edges}, requested rebinning to {edges}",
        )

    # If you rebin to a subset of initial range, keep the overflow and underflow
    overflow = ax.traits.overflow or (edges[-1] < ax.edges[-1] and not np.isclose(edges[-1], ax.edges[-1]))
    underflow = ax.traits.underflow or (edges[0] > ax.edges[0] and not np.isclose(edges[0], ax.edges[0]))
    flow = overflow or underflow
    new_ax = hist.axis.Variable(edges, name=ax.name, overflow=overflow, underflow=underflow)
    axes = list(h.axes)
    axes[ax_idx] = new_ax

    hnew = hist.Hist(*axes, name=h.name, storage=h._storage_type())

    # Offset from bin edge to avoid numeric issues
    offset = 0.5 * np.min(ax.edges[1:] - ax.edges[:-1])
    edges_eval = edges + offset
    edge_idx = ax.index(edges_eval)
    # Avoid going outside the range, reduceat will add the last index anyway
    if edge_idx[-1] == ax.size + ax.traits.overflow:
        edge_idx = edge_idx[:-1]

    if underflow:
        # Only if the original axis had an underflow should you offset
        if ax.traits.underflow:
            edge_idx += 1
        edge_idx = np.insert(edge_idx, 0, 0)

    # Take is used because reduceat sums i:len(array) for the last entry, in the case
    # where the final bin isn't the same between the initial and rebinned histogram, you
    # want to drop this value. Add tolerance of 1/2 min bin width to avoid numeric issues
    hnew.values(flow=flow)[...] = np.add.reduceat(h.values(flow=flow), edge_idx,
            axis=ax_idx).take(indices=range(new_ax.size + underflow + overflow), axis=ax_idx)
    if hnew._storage_type() == hist.storage.Weight():
        hnew.variances(flow=flow)[...] = np.add.reduceat(h.variances(flow=flow), edge_idx,
                axis=ax_idx).take(indices=range(new_ax.size + underflow + overflow), axis=ax_idx)
    return hnew


def optimise_binning1d(
    calculator,
    hists: dict[str, hist.Hist],
    target_uncertainty: float | None = 0.05,
    premade_edges: np.ndarray | None = None,
    variable: str | None = None,
) -> dict[str, hist.Hist]:
    """
    Optimise the binning of a set of histograms to achieve a target uncertainty
    """

    variables = calculator.variables[0]
    if variable is None:
        variable = variables.split("-")[0]

    efficiencies = {
        calculator.weight_producers[0]: {},
        calculator.weight_producers[1]: {},
    }
    efficiency_unc = {
        calculator.weight_producers[0]: {},
        calculator.weight_producers[1]: {},
    }

    bins_optimised = False
    # get edges
    if premade_edges is not None:
        edges = premade_edges
        # apply edges
        for weight_producer in calculator.weight_producers:
            hist = hists[weight_producer][variables]
            hist = rebin_hist(hist, variable, edges)
            hists[weight_producer][variables] = hist
        bins_optimised = True
    else:
        edges = hists[calculator.weight_producers[0]][variables].axes[variable].edges

    while not bins_optimised:
        # apply edges
        for weight_producer in calculator.weight_producers:
            hist = hists[weight_producer][variables]
            hist = rebin_hist(hist, variable, edges)
            hists[weight_producer][variables] = hist

        # calculate scale factors and uncertainties
        for weight_producer in calculator.weight_producers:
            # calculate efficiencies. process, shift, variable, bin
            efficiencies[weight_producer], efficiency_unc[weight_producer] = calculate_efficiencies(
                hists[weight_producer][calculator.variables[0]][:, ..., :], calculator.trigger
                )

        # calculate scale factors, second weight producer is used
        scale_factors = np.nan_to_num(
            efficiencies[calculator.weight_producers[1]][0] / efficiencies[calculator.weight_producers[1]][1],
            nan=1,
            posinf=1,
            neginf=1,
            )
        # calculate alpha factors
        alpha_factors = np.nan_to_num(
            efficiencies[calculator.weight_producers[0]][1] / efficiencies[calculator.weight_producers[1]][1],
            nan=1,
            posinf=1,
            neginf=1,
            )

        # only use the efficiencies and uncertainties of the second weight producer
        efficiencies = efficiencies[calculator.weight_producers[1]]
        efficiency_unc = efficiency_unc[calculator.weight_producers[1]]
        # calculate scale factor uncertainties, only statistical uncertainties are considered right now
        uncertainties = calc_sf_uncertainty(
            efficiencies, efficiency_unc, alpha_factors
            )

        # check for uncertainties larger than 5%
        rel_unc = uncertainties / scale_factors
        low_stat_bins = np.where(rel_unc > target_uncertainty)[0]
        # maybe np.where((rel_unc > target_uncertainty) or rel_unc == 0.0)[0] to merge empty bins?

        # merge bins
        if len(low_stat_bins) > 0 and edges[low_stat_bins[0]+1] != 400.0:
            edges = np.delete(edges, low_stat_bins[0]+1)
        else:
            bins_optimised = True

        # merge empty bins
        empty_bins = np.where(rel_unc == 0.0)[0]
        if len(empty_bins) > 1 and [edges[empty_bins[0]], edges[empty_bins[1]]] != [0.0, 400.0]:
            edges = np.delete(edges, empty_bins[1])

    logger.info(f"new edges: {edges}")

    return hists, edges


def optimise_binning2d(
    calculator,
    hists: dict[str, hist.Hist],
    target_uncertainty1: float | None = 0.01,
    target_uncertainty2: float | None = 0.05,
    premade_edges: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """
    Optimise the binning of a set of histograms to achieve a target uncertainty in 2 dimensions
    target_uncertainty1 is for the first optimization and should be small enough to yield usable uncertainties
    when binning in the second dimension
    """

    variables = calculator.variables[0]
    variable = variables.split("-")

    # optimise first axis
    hists1 = {
        calculator.weight_producers[0]: {},
        calculator.weight_producers[1]: {},
    }
    for weight_producer in calculator.weight_producers:
        hist1 = hists[weight_producer][variables][{f"{variable[1]}": sum}]
        hists1[weight_producer][variables] = hist1

    logger.info("Optimising first axis")

    hists1, edges1 = optimise_binning1d(
        calculator, hists1, target_uncertainty1, variable=variable[0]
    )

    # apply edges
    for weight_producer in calculator.weight_producers:
        hist = hists[weight_producer][variables]
        hist = rebin_hist(hist, variable[0], edges1)
        hists[weight_producer][variables] = hist

    logger.info("Optimising second axis")

    # optimise first axis
    edges2 = {}
    histslices = {}
    for subslice in range(len(hists[weight_producer][variables].axes[1].centers)):
        hists2 = {
            calculator.weight_producers[0]: {},
            calculator.weight_producers[1]: {},
        }
        for weight_producer in calculator.weight_producers:
            hist2 = hists[weight_producer][variables][:, subslice, :, :]
            hists2[weight_producer][variables] = hist2

        histslices[subslice], edges2[subslice] = optimise_binning1d(
            calculator, hists2, target_uncertainty2, variable=variable[1]
        )

    return histslices, edges2
