from columnflow.columnar_util import flat_np_view, layout_ak_array, set_ak_column
from columnflow.selection import SelectionResult, Selector, selector
from columnflow.util import InsertableDict, maybe_import

from azh.util import masked_sorted_indices

ak = maybe_import("awkward")
np = maybe_import("numpy")

# NanoAOD v15 jet-ID correctionlib inputs, in the order the payload declares them
JET_ID_INPUTS = [
    "eta",
    "chHEF",
    "neHEF",
    "chEmEF",
    "neEmEF",
    "muEF",
    "chMultiplicity",
    "neMultiplicity",
]


@selector(
    # the b-tag discriminator column is era-dependent (ParticleNet for 2022/23,
    # UParT for 2024) and is added dynamically in jet_selection_init below
    # Jet ID columns are era-dependent (v12 bitmap vs v15 recomputation) and the
    # b-tag discriminator likewise; both are added in jet_selection_init below
    uses={"Jet.pt", "Jet.eta", "Jet.phi"},
    produces={
        "cutflow.n_jet",
        "cutflow.n_jet_loose",
        "cutflow.n_bjet",
        "cutflow.jet1_pt",
        "cutflow.jet2_pt",
        "cutflow.jet3_pt",
        "cutflow.jet4_pt",
        "cutflow.jet1_eta",
        "cutflow.jet2_eta",
        "cutflow.jet3_eta",
        "cutflow.jet4_eta",
    },
    exposed=True,
)
def jet_selection(
    self: Selector,
    events: ak.Array,
    **kwargs,
) -> tuple[ak.Array, SelectionResult]:

    # assign local index to all Jets
    events = set_ak_column(events, "Jet.local_index", ak.local_index(events.Jet))

    # ── Jet ID ──
    # v12 stores the bitmap (bit1 = tight, bit2 = tightLepVeto, so ==6 is both).
    # v15 removed it; recompute from PF fractions via the JME payload. The
    # lepveto mask is AND-ed with tight so both paths mean the same thing.
    jid = self.config_inst.x.jet_id
    if jid.from_correctionlib:
        ch = flat_np_view(events.Jet.chMultiplicity, axis=1)
        ne = flat_np_view(events.Jet.neMultiplicity, axis=1)
        args = tuple(flat_np_view(events.Jet[f], axis=1) for f in JET_ID_INPUTS) + (
            ch + ne,
        )
        jet_id_tight = layout_ak_array(
            np.asarray(self.jet_id_tight_corr.evaluate(*args)) > 0.5,
            events.Jet.pt,
        )
        jet_id_lepveto = jet_id_tight & layout_ak_array(
            np.asarray(self.jet_id_lepveto_corr.evaluate(*args)) > 0.5,
            events.Jet.pt,
        )
    else:
        jet_id_tight = events.Jet.jetId >= 2
        jet_id_lepveto = events.Jet.jetId == 6

    # ── Loose jets (paper Table 1: pT > 15 GeV, |eta| < 4.7) ──
    # Used only for the ≥4-jet multiplicity cut
    loose_jet_mask = (
        (events.Jet.pt > 15)
        & (abs(events.Jet.eta) < 4.7)
        & jet_id_tight
        &
        # Run-3 EE-noise veto: within 2.5 < |eta| < 3.0, require pt > 50 GeV
        (
            (events.Jet.pt > 50)
            | (abs(events.Jet.eta) <= 2.5)
            | (abs(events.Jet.eta) >= 3.0)
        )
    )
    loose_jet_sel = ak.num(events.Jet[loose_jet_mask]) >= 2  # floor; >=4 is a category
    # also store a version that always passes (jet cut moved to categories)
    events = set_ak_column(
        events, "cutflow.n_jet_loose", ak.sum(loose_jet_mask, axis=1)
    )

    # ── Tight jets (pT > 30 GeV, |eta| < 2.5, tightLepVeto) ──
    # Used for b-tagging and the main jet collection
    jet_mask = (events.Jet.pt > 30) & (abs(events.Jet.eta) < 2.5) & jet_id_lepveto
    events = set_ak_column(events, "cutflow.n_jet", ak.sum(jet_mask, axis=1))

    # ── B-tagging (medium WP on tight jets) ──
    # tagger and WP come from cfg.x.btag_default: ParticleNet for 2022/23,
    # UParT for 2024 (BTV published no ParticleNet WPs for 2024)
    btag = self.config_inst.x.btag_default
    bjet_mask = jet_mask & (events.Jet[btag.column] >= btag.wp)
    events = set_ak_column(events, "cutflow.n_bjet", ak.sum(bjet_mask, axis=1))

    jet_indices = masked_sorted_indices(jet_mask, events.Jet.pt)
    bjet_indices = masked_sorted_indices(bjet_mask, events.Jet.pt)

    jets = events.Jet[jet_indices]
    padded_jets = ak.pad_none(jets, 4)
    for i in range(4):
        events = set_ak_column(
            events,
            f"cutflow.jet{i + 1}_pt",
            ak.where(
                (ak.is_none(padded_jets.pt[:, {i}][:, 0])),
                -100,
                (padded_jets.pt[:, {i}][:, 0]),
            ),
        )
        events = set_ak_column(
            events,
            f"cutflow.jet{i + 1}_eta",
            ak.where(
                (ak.is_none(padded_jets.eta[:, {i}][:, 0])),
                -100,
                (padded_jets.eta[:, {i}][:, 0]),
            ),
        )

    loose_jet_sel = ak.fill_none(loose_jet_sel, False)
    jet_mask = ak.fill_none(jet_mask, False)

    # Selection step uses LOOSE jets (≥4 with pT>15, |eta|<4.7)
    return events, SelectionResult(
        steps={
            "Jet": loose_jet_sel,
        },
        objects={
            "Jet": {
                "Jet": jet_indices,
                "BJet": bjet_indices,
            },
        },
        aux={
            "jet_mask": jet_mask,
            "n_central_jets": ak.num(jet_indices),
        },
    )


@jet_selection.init
def jet_selection_init(self: Selector, **kwargs) -> None:
    self.uses.add(f"Jet.{self.config_inst.x.btag_default.column}")
    if self.config_inst.x.jet_id.from_correctionlib:
        self.uses |= {f"Jet.{f}" for f in JET_ID_INPUTS}
    else:
        self.uses.add("Jet.jetId")


@jet_selection.requires
def jet_selection_requires(self: Selector, reqs: dict) -> None:
    if not self.config_inst.x.jet_id.from_correctionlib:
        return
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles

    reqs["external_files"] = BundleExternalFiles.req(self.task)


@jet_selection.setup
def jet_selection_setup(
    self: Selector,
    reqs: dict,
    inputs: dict,
    reader_targets: InsertableDict,
) -> None:
    jid = self.config_inst.x.jet_id
    if not jid.from_correctionlib:
        return
    import correctionlib

    bundle = reqs["external_files"]
    cset = correctionlib.CorrectionSet.from_string(
        bundle.files.jet_id.load(formatter="gzip").decode("utf-8"),
    )
    self.jet_id_tight_corr = cset[jid.tight]
    self.jet_id_lepveto_corr = cset[jid.tight_lepveto]
