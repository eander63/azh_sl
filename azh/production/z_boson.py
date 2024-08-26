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
    # leptons = events.Lepton
    # leptons = ak.pad_none(leptons,3)
    z = events.Leptons[:, 0] + events.Leptons[:, 1]
    mass_z = z.mass
    mass_z = ak.where(np.isfinite(mass_z), mass_z, ak.full_like(mass_z, 0))
    events = set_ak_column(events, "m_z", mass_z)
    events = set_ak_column(events, "pt_z", z.pt)
    return events
