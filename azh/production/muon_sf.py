"""
Muon ID and isolation scale factors with separate statistical and systematic
variations (MUO recommendation: syst correlated across eras, stat per era).

columnflow's muon_weights only offers systup/systdown. For muon_Z.json those
keys are the nominal +- the COMBINED uncertainty for the ID SF, but for other
corrections in the same file systup equals the nominal (syst-only), so they
cannot be used to split the two. The "stat" and "syst" keys are the absolute
components (checked: sqrt(stat^2 + syst^2) = systup - nominal for TightID).

Produces, for <w> in muon_id_weight, muon_iso_weight:
    <w>, <w>_stat_{up,down}, <w>_syst_{up,down}
Variations move all muons of an event coherently.
"""

from __future__ import annotations

import json

from columnflow.columnar_util import set_ak_column
from columnflow.production import Producer, producer
from law.util import InsertableDict
from columnflow.util import maybe_import

np = maybe_import("numpy")
ak = maybe_import("awkward")

SF_KINDS = {
    "muon_id_weight": "muon_sf_id_names",
    "muon_iso_weight": "muon_sf_iso_names",
}


def pt_range_from_json(cset_json: dict, name: str) -> tuple[float, float]:
    """(first, last) pT edge of correction *name*, over all its pT binnings."""
    corr = next(c for c in cset_json["corrections"] if c["name"] == name)
    lo, hi = [], []

    def walk(node):
        if isinstance(node, dict):
            if node.get("nodetype") == "binning" and node.get("input") == "pt":
                lo.append(float(node["edges"][0]))
                hi.append(float(node["edges"][-1]))
            elif node.get("nodetype") == "multibinning" and "pt" in node.get("inputs", []):
                e = node["edges"][node["inputs"].index("pt")]
                lo.append(float(e[0]))
                hi.append(float(e[-1]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(corr["data"])
    if not lo:
        return (0.0, float("inf"))
    return (min(lo), max(hi))


@producer(
    uses={"Muon.{pt,eta,tightId,pfRelIso04_all}"},
    produces={
        f"{w}{post}"
        for w in SF_KINDS
        for post in ("", "_stat_up", "_stat_down", "_syst_up", "_syst_down")
    },
    mc_only=True,
)
def muon_sf_weights(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    mu = events.Muon
    mask = mu.tightId & (mu.pfRelIso04_all < 0.15) & (mu.pt >= self.config_inst.x.muon_sf_pt_min)
    mu = mu[mask]
    counts = ak.num(mu.pt)
    pt = ak.to_numpy(ak.flatten(mu.pt)).astype(np.float64)
    eta = ak.to_numpy(ak.flatten(mu.eta)).astype(np.float64)

    for weight_name, corr in self.sf_corrs.items():
        lo, hi = self.pt_ranges[weight_name]
        ptc = np.clip(pt, lo, np.nextafter(hi, lo))
        nom = corr.evaluate(eta, ptc, "nominal")
        unc = {"stat": corr.evaluate(eta, ptc, "stat"), "syst": corr.evaluate(eta, ptc, "syst")}

        def prod(values):
            return ak.values_astype(ak.prod(ak.unflatten(values, counts), axis=1), np.float32)

        events = set_ak_column(events, weight_name, prod(nom))
        for kind, u in unc.items():
            events = set_ak_column(events, f"{weight_name}_{kind}_up", prod(nom + u))
            events = set_ak_column(events, f"{weight_name}_{kind}_down", prod(nom - u))
    return events


@muon_sf_weights.requires
def muon_sf_weights_requires(self: Producer, task, reqs: dict, **kwargs) -> None:
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles
    reqs["external_files"] = BundleExternalFiles.req(task)


@muon_sf_weights.setup
def muon_sf_weights_setup(
    self: Producer,
    task,
    reqs: dict,
    inputs: dict,
    reader_targets: InsertableDict,
    **kwargs,
) -> None:
    import correctionlib

    text = reqs["external_files"].files.muon_sf.load(formatter="gzip").decode("utf-8")
    cset = correctionlib.CorrectionSet.from_string(text)
    cset_json = json.loads(text)
    self.sf_corrs, self.pt_ranges = {}, {}
    for weight_name, cfg_key in SF_KINDS.items():
        name = self.config_inst.x(cfg_key)[0]
        self.sf_corrs[weight_name] = cset[name]
        self.pt_ranges[weight_name] = pt_range_from_json(cset_json, name)
