"""
Theory and normalization weights that columnflow does not provide in the form
this analysis needs.

pdf_hessian_weights
    PDF + alpha_s uncertainty for the NNPDF3.1 "mc_hessian_pdfas" set used by
    the Run 3 samples (LHA 325300, ErrorType symmhessian+as, 103 members:
    [0] nominal, [1-100] symmetric Hessian eigenvectors, [101, 102] alpha_s =
    0.116 / 0.120 around 0.118). columnflow's combined mode uses the MC-replica
    68%-width formula, which is wrong for a Hessian set. Here, with
    w_i = LHEPdfWeight[i] / LHEPdfWeight[0]:
        d_pdf = sqrt(sum_{i=1..100} (w_i - 1)^2)
        d_as  = cfg.x.pdf_alphas_scale * (w_102 - w_101) / 2
        pdf_weight_{up,down} = 1 +- sqrt(d_pdf^2 + d_as^2)
    cfg.x.pdf_alphas_scale = 0.0015 / 0.002 rescales the +-0.002 members to the
    PDF4LHC +-0.0015. Events without exactly 103 weights get weight 1; a dataset
    in which no event has 103 weights raises (it uses a different PDF set).

ps_weights
    Parton-shower ISR/FSR variations from PSWeight (documented layout:
    [0] ISR=2 FSR=1, [1] ISR=1 FSR=2, [2] ISR=0.5 FSR=1, [3] ISR=1 FSR=0.5).
    Normalized per process in production, like the scale weights.

lumi_weight
    Luminosity as a weight shift so it appears in plot uncertainty bands:
    1 +- the quadrature sum of this era's LUM nuisances. The datacard takes the
    luminosity from cfg.x.luminosity (lnN) instead; do not add this shift there.
"""

from columnflow.columnar_util import set_ak_column
from columnflow.production import Producer, producer
from columnflow.util import maybe_import

import law

np = maybe_import("numpy")
ak = maybe_import("awkward")

logger = law.logger.get_logger(__name__)

N_PDF_MEMBERS = 103


@producer(
    uses={"LHEPdfWeight"},
    produces={"pdf_weight", "pdf_weight_up", "pdf_weight_down"},
    mc_only=True,
)
def pdf_hessian_weights(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    lhe = events.LHEPdfWeight
    valid = ak.to_numpy(ak.num(lhe, axis=1) == N_PDF_MEMBERS)
    if not valid.any():
        raise ValueError(
            f"dataset {self.dataset_inst.name}: no event has {N_PDF_MEMBERS} LHEPdfWeights; "
            "it uses a PDF set other than NNPDF31_nnlo_as_0118_mc_hessian_pdfas (325300) "
            "and needs its own treatment",
        )
    if not valid.all():
        logger.warning(
            f"dataset {self.dataset_inst.name}: {100 * (1 - valid.mean()):.2f}% of events do not have "
            f"{N_PDF_MEMBERS} LHEPdfWeights; their pdf weights are set to 1",
        )

    w = np.ones((len(events), N_PDF_MEMBERS), dtype=np.float64)
    if valid.any():
        w[valid] = ak.to_numpy(lhe[valid]).astype(np.float64)
    nominal = w[:, 0:1]
    bad_nominal = nominal[:, 0] == 0
    w = np.where(nominal != 0, w / np.where(nominal != 0, nominal, 1.0), 1.0)

    d_pdf = np.sqrt(np.sum((w[:, 1:101] - 1.0) ** 2, axis=1))
    d_as = self.config_inst.x.pdf_alphas_scale * 0.5 * (w[:, 102] - w[:, 101])
    delta = np.sqrt(d_pdf ** 2 + d_as ** 2)
    delta[~valid | bad_nominal] = 0.0

    events = set_ak_column(events, "pdf_weight", np.ones(len(events), dtype=np.float32))
    events = set_ak_column(events, "pdf_weight_up", (1.0 + delta).astype(np.float32))
    events = set_ak_column(events, "pdf_weight_down", np.maximum(1.0 - delta, 0.0).astype(np.float32))
    return events


# PSWeight index for each variation (NanoAOD branch documentation)
PS_INDEX = {
    ("isr", "up"): 0,
    ("fsr", "up"): 1,
    ("isr", "down"): 2,
    ("fsr", "down"): 3,
}


@producer(
    uses={"PSWeight"},
    produces={f"{v}_weight{p}" for v in ("isr", "fsr") for p in ("", "_up", "_down")},
    mc_only=True,
)
def ps_weights(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    ps = events.PSWeight
    valid = ak.to_numpy(ak.num(ps, axis=1) == 4)
    if not valid.all():
        logger.warning(
            f"dataset {self.dataset_inst.name}: {100 * (1 - valid.mean()):.2f}% of events do not have "
            "4 PSWeights; their ISR/FSR weights are set to 1",
        )
    arr = np.ones((len(events), 4), dtype=np.float32)
    if valid.any():
        arr[valid] = ak.to_numpy(ps[valid]).astype(np.float32)
    ones = np.ones(len(events), dtype=np.float32)
    for var in ("isr", "fsr"):
        events = set_ak_column(events, f"{var}_weight", ones)
        for d in ("up", "down"):
            events = set_ak_column(events, f"{var}_weight_{d}", arr[:, PS_INDEX[(var, d)]])
    return events


@producer(
    produces={"lumi_weight", "lumi_weight_up", "lumi_weight_down"},
    mc_only=True,
)
def lumi_weight(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    lumi = self.config_inst.x.luminosity
    rel = float(np.sqrt(sum(
        float(lumi.get(names=name, direction="up", factor=True) - 1.0) ** 2
        for name in lumi.uncertainties
    )))
    ones = np.ones(len(events), dtype=np.float32)
    events = set_ak_column(events, "lumi_weight", ones)
    events = set_ak_column(events, "lumi_weight_up", ones * np.float32(1.0 + rel))
    events = set_ak_column(events, "lumi_weight_down", ones * np.float32(1.0 - rel))
    return events
