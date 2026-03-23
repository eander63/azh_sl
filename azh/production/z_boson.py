# coding: utf-8

"""
Producer for Z-boson kinematic quantities (m_z, pt_z).

Depends on choose_lepton having already built events.Leptons as a
collection of exactly 2 LorentzVectors (the best OSSF pair).
"""
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
from columnflow.production import Producer, producer
from azh.production.leptons import choose_lepton

np = maybe_import("numpy")
ak = maybe_import("awkward")


@producer(
    uses={
        choose_lepton,
    },
    produces={
        "m_z", "pt_z",
    },
)
def z_boson(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Compute the invariant mass and transverse momentum of the Z candidate
    from the two leptons stored in events.Leptons.

    choose_lepton guarantees exactly 2 entries for events passing the
    lepton selection. For any edge-case events with fewer than 2 leptons
    we return 0.
    """
    leptons = events.Leptons
    has_pair = ak.num(leptons, axis=1) >= 2

    # pad to at least 2 slots so we can index safely
    padded = ak.pad_none(leptons, 2, axis=1)

    # compute 4-vector sum only where both leptons exist
    # compute 4-vector sum — use zeros_like as fallback to avoid None issues
    sum_4vec_mass = (padded[:, 0] + padded[:, 1]).mass
    sum_4vec_pt   = (padded[:, 0] + padded[:, 1]).pt
    z_mass = ak.fill_none(
        ak.where(has_pair, sum_4vec_mass, ak.zeros_like(sum_4vec_mass)),
        0.0,
    )
    z_pt = ak.fill_none(
        ak.where(has_pair, sum_4vec_pt, ak.zeros_like(sum_4vec_pt)),
        0.0,
    )

    # guard against any remaining NaN/Inf
    z_mass = ak.where(np.isfinite(z_mass), z_mass, ak.zeros_like(z_mass))
    z_pt   = ak.where(np.isfinite(z_pt),   z_pt,   ak.zeros_like(z_pt))

    events = set_ak_column(events, "m_z",  z_mass)
    events = set_ak_column(events, "pt_z", z_pt)
    return events
