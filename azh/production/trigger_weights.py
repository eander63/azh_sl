# coding: utf-8
"""
Producers for trigger scale factors.
Muon: NUM_IsoMu24_or_Mu50_or_CascadeMu100_or_HighPtTkMu100_DEN_CutBasedIdGlobalHighPt_and_TkIsoLoose
Electron: Electron-HLT-SF
Strategy: apply SF for the leading lepton that fired the trigger.
For mumu events: SF on leading muon passing IsoMu24 threshold (pt > 26).
For ee events: SF on leading electron passing Ele30 threshold (pt > 32).
"""

from columnflow.production import Producer, producer
from columnflow.util import maybe_import, InsertableDict
from columnflow.columnar_util import set_ak_column

np = maybe_import("numpy")
ak = maybe_import("awkward")


@producer(
    uses={
        "Muon.pt", "Muon.eta",
        "Electron.pt", "Electron.eta",
        "cutflow.n_muo_loose", "cutflow.n_ele_loose",
    },
    produces={
        "muon_trig_weight", "muon_trig_weight_up", "muon_trig_weight_down",
        "electron_trig_weight", "electron_trig_weight_up", "electron_trig_weight_down",
    },
    mc_only=True,
)
def trigger_weights(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Apply trigger SFs to the leading lepton in mumu (muon trig) and ee (electron trig) events.
    Events with no qualifying lepton get SF=1.
    """
    ones = ak.ones_like(events.event, dtype=np.float32)

    # --- Muon trigger SF ---
    is_mumu = events.cutflow.n_muo_loose >= 2

    padded_muo = ak.pad_none(events.Muon, 1, axis=1)
    lead_muo_pt  = ak.to_numpy(ak.fill_none(padded_muo[:, 0].pt,  30.0))
    lead_muo_eta = ak.to_numpy(ak.fill_none(padded_muo[:, 0].eta, 0.0))

    lead_muo_pt = np.clip(lead_muo_pt, 26.1, 199.9)

    muo_sf    = self.muon_trig_corr.evaluate(lead_muo_eta, lead_muo_pt, "nominal")
    muo_sf_up = self.muon_trig_corr.evaluate(lead_muo_eta, lead_muo_pt, "systup")
    muo_sf_dn = self.muon_trig_corr.evaluate(lead_muo_eta, lead_muo_pt, "systdown")

    muon_trig_weight    = ak.where(is_mumu, ak.Array(muo_sf),    ones)
    muon_trig_weight_up = ak.where(is_mumu, ak.Array(muo_sf_up), ones)
    muon_trig_weight_dn = ak.where(is_mumu, ak.Array(muo_sf_dn), ones)

    events = set_ak_column(events, "muon_trig_weight",      ak.values_astype(muon_trig_weight,    np.float32))
    events = set_ak_column(events, "muon_trig_weight_up",   ak.values_astype(muon_trig_weight_up, np.float32))
    events = set_ak_column(events, "muon_trig_weight_down", ak.values_astype(muon_trig_weight_dn, np.float32))

    # --- Electron trigger SF ---
    is_ee = events.cutflow.n_ele_loose >= 2

    padded_ele = ak.pad_none(events.Electron, 1, axis=1)
    lead_ele_pt  = ak.to_numpy(ak.fill_none(padded_ele[:, 0].pt,  35.0))
    lead_ele_eta = ak.to_numpy(ak.fill_none(padded_ele[:, 0].eta, 0.0))

    lead_ele_pt = np.clip(lead_ele_pt, 32.1, 498.9)

    _, ele_trig_year, ele_trig_path = self.config_inst.x.electron_sf_trig_names

    ele_sf    = self.electron_trig_corr.evaluate(ele_trig_year, "sf",     ele_trig_path, lead_ele_eta, lead_ele_pt)
    ele_sf_up = self.electron_trig_corr.evaluate(ele_trig_year, "sfup",   ele_trig_path, lead_ele_eta, lead_ele_pt)
    ele_sf_dn = self.electron_trig_corr.evaluate(ele_trig_year, "sfdown", ele_trig_path, lead_ele_eta, lead_ele_pt)

    electron_trig_weight    = ak.where(is_ee, ak.Array(ele_sf),    ones)
    electron_trig_weight_up = ak.where(is_ee, ak.Array(ele_sf_up), ones)
    electron_trig_weight_dn = ak.where(is_ee, ak.Array(ele_sf_dn), ones)

    events = set_ak_column(events, "electron_trig_weight",      ak.values_astype(electron_trig_weight,    np.float32))
    events = set_ak_column(events, "electron_trig_weight_up",   ak.values_astype(electron_trig_weight_up, np.float32))
    events = set_ak_column(events, "electron_trig_weight_down", ak.values_astype(electron_trig_weight_dn, np.float32))

    return events


@trigger_weights.requires
def trigger_weights_requires(self: Producer, reqs: dict) -> None:
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles
    reqs["external_files"] = BundleExternalFiles.req(self.task)


@trigger_weights.setup
def trigger_weights_setup(
    self: Producer,
    reqs: dict,
    inputs: dict,
    reader_targets: InsertableDict,
) -> None:
    bundle = reqs["external_files"]

    import correctionlib
    correctionlib.highlevel.Correction.__call__ = correctionlib.highlevel.Correction.evaluate

    # muon trigger SF
    muon_trig_name, _ = self.config_inst.x.muon_sf_trig_names
    cset_muo = correctionlib.CorrectionSet.from_string(
        bundle.files.muon_sf.load(formatter="gzip").decode("utf-8"),
    )
    self.muon_trig_corr = cset_muo[muon_trig_name]

    # electron trigger SF
    ele_trig_name, _, _ = self.config_inst.x.electron_sf_trig_names
    cset_ele = correctionlib.CorrectionSet.from_string(
        bundle.files.electron_sf_hlt.load(formatter="gzip").decode("utf-8"),
    )
    self.electron_trig_corr = cset_ele[ele_trig_name]
