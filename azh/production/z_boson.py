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
    leptons = events.Leptons
    # pad to 2, use None for missing leptons
    padded = ak.pad_none(leptons, 2)
    l1 = ak.fill_none(padded[:, 0], padded[:, 0])
    l2 = ak.fill_none(padded[:, 1], padded[:, 1])
    # compute z only where both leptons exist
    has_pair = ak.num(leptons) >= 2
    z_mass = ak.where(has_pair, (padded[:, 0] + padded[:, 1]).mass, 0.0)
    z_pt = ak.where(has_pair, (padded[:, 0] + padded[:, 1]).pt, 0.0)
    z_mass = ak.fill_none(z_mass, 0.0)
    z_pt = ak.fill_none(z_pt, 0.0)
    mass_z = ak.where(np.isfinite(z_mass), z_mass, ak.full_like(z_mass, 0))
    events = set_ak_column(events, "m_z", mass_z)
    events = set_ak_column(events, "pt_z", z_pt)
    return events
