# coding: utf-8

"""
Column producers related to leptons.

For Run3: after ReduceEvents only pt/eta/phi/mass/pdgId/charge survive for
Muon and Electron. Computes the best OSSF pair closest to the Z pole using
manual 4-vector arithmetic to avoid coffea behavior propagation issues
through ak.combinations.
"""
from columnflow.production import Producer, producer
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column

ak = maybe_import("awkward")
np = maybe_import("numpy")
coffea = maybe_import("coffea")
maybe_import("coffea.nanoevents.methods.nanoaod")

M_Z = 91.188  # PDG Z-pole mass in GeV


def invariant_mass(pt1, eta1, phi1, mass1, pt2, eta2, phi2, mass2):
    """Compute invariant mass of two particles from pt/eta/phi/mass."""
    px1 = pt1 * np.cos(phi1)
    py1 = pt1 * np.sin(phi1)
    pz1 = pt1 * np.sinh(eta1)
    e1  = np.sqrt(px1**2 + py1**2 + pz1**2 + mass1**2)
    px2 = pt2 * np.cos(phi2)
    py2 = pt2 * np.sin(phi2)
    pz2 = pt2 * np.sinh(eta2)
    e2  = np.sqrt(px2**2 + py2**2 + pz2**2 + mass2**2)
    m2  = (e1+e2)**2 - (px1+px2)**2 - (py1+py2)**2 - (pz1+pz2)**2
    return np.sqrt(ak.where(m2 > 0, m2, ak.zeros_like(m2)))


@producer(
    uses={
        "Electron.pt", "Electron.eta", "Electron.phi", "Electron.mass",
        "Electron.pdgId", "Electron.charge",
        "Muon.pt", "Muon.eta", "Muon.phi", "Muon.mass",
        "Muon.pdgId", "Muon.charge",
    },
    produces={
        "Leptons.pt", "Leptons.eta", "Leptons.phi", "Leptons.mass",
        "Leptons.pdgId",
    },
)
def choose_lepton(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Build an OSSF lepton pair (ee or mumu) whose invariant mass is closest
    to the Z pole, and store it as Leptons.

    Uses manual 4-vector arithmetic throughout to avoid coffea behavior
    propagation issues through ak.combinations.
    """

    def best_ossf_pair(collection):
        """
        Return the best OS pair from a same-flavour collection,
        selecting the pair with invariant mass closest to M_Z.
        Returns a (n_events, 2) array, None-padded where no pair exists.
        """
        pairs = ak.combinations(collection, 2, axis=1, fields=["l1", "l2"])
        # opposite-sign requirement
        ossf = pairs[pairs.l1.charge * pairs.l2.charge < 0]
        # compute invariant mass manually
        m_inv = invariant_mass(
            ossf.l1.pt, ossf.l1.eta, ossf.l1.phi, ossf.l1.mass,
            ossf.l2.pt, ossf.l2.eta, ossf.l2.phi, ossf.l2.mass,
        )
        delta = abs(m_inv - M_Z)
        best_idx = ak.argmin(delta, axis=1, keepdims=True)
        best_pair = ossf[best_idx]
        # after argmin+keepdims, best_pair has shape (n_events, <=1)
        # pad to ensure every event has exactly 1 entry (None if no OSSF pair)
        best_pair = ak.pad_none(best_pair, 1, axis=1)
        # extract l1/l2 — shape is now (n_events,) with possible None
        l1 = best_pair[:, 0].l1
        l2 = best_pair[:, 0].l2
        # stack into (n_events, 2)
        return ak.concatenate([l1[:, np.newaxis], l2[:, np.newaxis]], axis=1)

    def pair_delta(pair):
        """Compute delta from Z pole for a (n_events, 2) pair array."""
        valid = ~(ak.is_none(pair[:, 0]) | ak.is_none(pair[:, 1]))
        pt1   = ak.fill_none(pair[:, 0].pt,   0.0)
        eta1  = ak.fill_none(pair[:, 0].eta,  0.0)
        phi1  = ak.fill_none(pair[:, 0].phi,  0.0)
        mass1 = ak.fill_none(pair[:, 0].mass, 0.0)
        pt2   = ak.fill_none(pair[:, 1].pt,   0.0)
        eta2  = ak.fill_none(pair[:, 1].eta,  0.0)
        phi2  = ak.fill_none(pair[:, 1].phi,  0.0)
        mass2 = ak.fill_none(pair[:, 1].mass, 0.0)
        mass = invariant_mass(pt1, eta1, phi1, mass1, pt2, eta2, phi2, mass2)
        return ak.where(valid, abs(mass - M_Z), ak.full_like(mass, 1e9))

    muon     = events.Muon[["pt", "eta", "phi", "mass", "pdgId", "charge"]]
    electron = events.Electron[["pt", "eta", "phi", "mass", "pdgId", "charge"]]

    mumu_pair = best_ossf_pair(muon)
    ee_pair   = best_ossf_pair(electron)

    mumu_delta = pair_delta(mumu_pair)
    ee_delta   = pair_delta(ee_pair)

    use_mumu = mumu_delta <= ee_delta

    l1 = ak.where(use_mumu, mumu_pair[:, 0], ee_pair[:, 0])
    l2 = ak.where(use_mumu, mumu_pair[:, 1], ee_pair[:, 1])

    leptons = ak.concatenate(
        [l1[:, np.newaxis], l2[:, np.newaxis]],
        axis=1,
    )

    leptons = ak.with_name(leptons, "PtEtaPhiMLorentzVector")
    events = set_ak_column(events, "Leptons", leptons)
    return events
