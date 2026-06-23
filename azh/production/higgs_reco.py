# Reconstruction of the heavy Higgs H
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
from columnflow.production import Producer, producer
# from azh.production.leptons import choose_lepton

np = maybe_import("numpy")
ak = maybe_import("awkward")


@producer(
    uses={
        "Jet", "BJet", "MET.pt", "MET.phi"
    },
    produces={
        "m_h", "m_a", "del_m", "n_jets", "n_bjets","deltaR_b_z","deltaPhi_MET_Jet1","deltaPhi_MET_Jet2","deltaPhi_MET_Jet3","MET_ht"
    },
)
def higgs_reco(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    jets = events.Jet
    bjets = events.BJet
    MET = events.MET

    index_jets = ak.argsort(jets.btagDeepFlavB, ascending=False, axis=-1)
    index_bjets = ak.argsort(bjets.btagDeepFlavB, ascending=False, axis=-1)
    sorted_jets = jets[index_jets]
    sorted_bjets = bjets[index_bjets]

    wp_med = self.config_inst.x.btag_working_points.deepjet.medium
    light_jets_mask = jets.btagDeepFlavB < wp_med
    light_jets = jets[light_jets_mask]

    # The h reconstruction below adds these objects as 4-vectors inside nested
    # ak.where branches. ak.where evaluates ALL branches for ALL events, so the
    # padded slots get added even for events that don't take that branch, and
    # "None + record" is not broadcastable (-> "cannot broadcast records in add").
    # Pad, then replace the None slots with a zero 4-vector (identity under
    # addition) so every branch is safe; the physically-wrong branches are
    # discarded by ak.where and the surviving quantities are sentineled downstream.
    def _safe_p4(objs, n):
        objs = ak.pad_none(objs, n, axis=1)
        return ak.zip(
            {
                "pt": ak.fill_none(objs.pt, 0.0),
                "eta": ak.fill_none(objs.eta, 0.0),
                "phi": ak.fill_none(objs.phi, 0.0),
                "mass": ak.fill_none(objs.mass, 0.0),
            },
            with_name="PtEtaPhiMLorentzVector",
            behavior=events.behavior,
        )

    sorted_bjets = _safe_p4(sorted_bjets, 2)
    light_jets = _safe_p4(light_jets, 6)
    sorted_jets = _safe_p4(sorted_jets, 6)
    
    num_jets = ak.num(events.Jet, axis=-1)
    num_bjets = ak.num(events.BJet, axis=-1)

    h = ak.where(
        num_jets == 4,
        ak.where(
            num_bjets > 2,
            sorted_jets[:, 0] + sorted_jets[:, 1] + sorted_jets[:, 2] + sorted_jets[:, 3],
            ak.where(
                num_bjets == 2,
                sorted_bjets[:, 0] + sorted_bjets[:, 1] + light_jets[:, 0] + light_jets[:, 1],
                ak.where(
                    num_bjets == 1,
                    sorted_bjets[:, 0] + light_jets[:, 0] + light_jets[:, 1] + light_jets[:, 2],
                    light_jets[:, 0] + light_jets[:, 1] + light_jets[:, 2] + light_jets[:, 3],
                ),
            ),
        ),
        ak.where(
            num_jets == 5,
            ak.where(
                num_bjets > 2,
                sorted_jets[:, 0] + sorted_jets[:, 1] + sorted_jets[:, 2] + sorted_jets[:, 3] + sorted_jets[:, 4],
                ak.where(
                    num_bjets == 2,
                    sorted_bjets[:, 0] + sorted_bjets[:, 1] + light_jets[:, 0] + light_jets[:, 1] + light_jets[:, 2],
                    ak.where(
                        num_bjets == 1,
                        sorted_bjets[:, 0] + light_jets[:, 0] + light_jets[:, 1] + light_jets[:, 2] + light_jets[:, 3],
                        light_jets[:, 0] + light_jets[:, 1] + light_jets[:, 2] + light_jets[:, 3] + light_jets[:, 4],
                    ),
                ),
            ),
            ak.where(
                num_bjets > 2,
                sorted_jets[:, 0] + sorted_jets[:, 1] + sorted_jets[:, 2] + sorted_jets[:, 3] + sorted_jets[:, 4] + sorted_jets[:, 5],
                ak.where(
                    num_bjets == 2,
                    sorted_bjets[:, 0] + sorted_bjets[:, 1] + light_jets[:, 0] + light_jets[:, 1] + light_jets[:, 2] + light_jets[:, 3],
                    ak.where(
                        num_bjets == 1,
                        sorted_bjets[:, 0] + light_jets[:, 0] + light_jets[:, 1] + light_jets[:, 2] + light_jets[:, 3] + light_jets[:, 4],
                        light_jets[:, 0] + light_jets[:, 1] + light_jets[:, 2] + light_jets[:, 3] + light_jets[:, 4] + light_jets[:, 5],
                    ),
                ),
            ),
        ),
    )

    mass_h = h.mass
    mass_h = ak.where(np.isfinite(mass_h), mass_h, ak.full_like(mass_h, 0))

    n_jets = ak.num(events.Jet, axis=-1)
    n_bjets = ak.num(events.BJet, axis=-1)
    events = set_ak_column(events, "m_h", mass_h)
    events = set_ak_column(events, "n_jets", n_jets)
    events = set_ak_column(events, "n_bjets", n_bjets)

    z = events.Leptons[:, 0] + events.Leptons[:, 1]
    mass_z = z.mass
    mass_z = ak.where(np.isfinite(mass_z), mass_z, ak.full_like(mass_z, 0))
    a = z + h
    mass_a = a.mass
    # leading_b = ak.where((ak.num(events.BJet, axis=-1) > 0),sorted_bjets[:, 0],)
    deltaR_b_z = np.sqrt(np.abs((sorted_bjets[:, 0].eta - z.eta)**2 + (sorted_bjets[:, 0].phi - z.phi)**2))
    # loosened baseline can yield 0 b-jets: sorted_bjets is padded to >=2 so the
    # positional access is safe, but sentinel the value where there is no b-jet
    deltaR_b_z = ak.where(n_bjets >= 1, deltaR_b_z, -1.0)
    mass_a = ak.where(np.isfinite(mass_a), mass_a, ak.full_like(mass_a, 0))
    del_m = mass_a - mass_h
    # del_m is only physically meaningful with a full >=4-jet reconstruction;
    # sentinel it elsewhere so the loosened baseline doesn't leak garbage masses
    del_m = ak.where(n_jets >= 4, del_m, -1.0)
    # from IPython import embed; embed()
    # `jets` (= events.Jet) is unpadded; the loosened baseline allows <4 jets, so
    # direct positional access throws. Pad to 4 for safe indexing and sentinel the
    # values outside the >=4-jet phase space (these vars are only used there).
    jets_p = ak.pad_none(jets, 4, axis=1)
    ht_den = jets_p[:, 0].pt + jets_p[:, 1].pt + jets_p[:, 2].pt + jets_p[:, 3].pt
    MET_ht = ak.where(n_jets >= 4, MET.pt / ht_den, -1.0)
    deltaPhi_MET_Jet1 = ak.where(n_jets >= 4, MET.phi - jets_p[:, 0].phi, -1.0)
    deltaPhi_MET_Jet2 = ak.where(n_jets >= 4, MET.phi - jets_p[:, 1].phi, -1.0)
    deltaPhi_MET_Jet3 = ak.where(n_jets >= 4, MET.phi - jets_p[:, 2].phi, -1.0)
    events = set_ak_column(events, "m_a", mass_a)
    events = set_ak_column(events, "del_m", del_m)
    events = set_ak_column(events, "deltaR_b_z", deltaR_b_z)
    events = set_ak_column(events, "deltaPhi_MET_Jet1", deltaPhi_MET_Jet1)
    events = set_ak_column(events, "deltaPhi_MET_Jet2", deltaPhi_MET_Jet2)
    events = set_ak_column(events, "deltaPhi_MET_Jet3", deltaPhi_MET_Jet3)
    events = set_ak_column(events, "MET_ht", MET_ht)
    return events
