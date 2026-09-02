# coding: utf-8

"""
Inference model for the AZH -> ZH -> ll tt semileptonic search (Run 3).

An "inference model" is the bridge between columnflow's histograms and combine.
It declares three things, and nothing else:

  * CATEGORIES  -- which (config category, variable) pair becomes one datacard
                   bin set, and which data datasets supply the observation.
  * PROCESSES   -- which config processes contribute to those categories, which
                   MC datasets they are built from, and which one is the signal.
  * PARAMETERS  -- the nuisance parameters, i.e. rate (lnN / lnU / rateParam)
                   and shape (morphing) uncertainties.

`cf.CreateDatacards` walks this structure, loads the matching histograms from
`cf.MergeHistograms`, and writes one `datacard.txt` + `shapes.root` per
category.

Reference: AN-2022/158 (Run 2 semileptonic AN), Sections 7.1, 8 and 9.

--------------------------------------------------------------------------
API GENERATION
--------------------------------------------------------------------------
This file targets the columnflow API generation that uses the FLAT keyword
form (`config_category=`, `config_variable=`, `config_mc_datasets=`,
`config_shift_source=`) and a single `self.config_inst`. That is what your
colleague's hadronic model uses, so your fork is on the same generation.

Newer upstream columnflow replaced all of these with a nested
`config_data={<config_name>: {...}}` dict and `self.config_insts` (plural).
If you ever bump the submodule and this file starts raising `TypeError` on
unexpected keyword arguments, that is the change you are hitting.

Because `self.config_inst` is singular, ONE INFERENCE MODEL COVERS ONE ERA.
Producing the full Run 3 result means running `cf.CreateDatacards` once per
config (2022pre/2022post/2023pre/2023post) and merging the outputs with
combine's `combineCards.py`. The `_era_key()` helper below exists so that the
nuisances the AN declares as year-uncorrelated get distinct names across those
four runs and are therefore NOT merged into one parameter by combineCards.
"""

from columnflow.inference import inference_model, ParameterType, ParameterTransformation

from azh.config.signals import AZH_SIGNAL_PROCESSES, masses


# --------------------------------------------------------------------------
# Analysis-level switches. These are the knobs you will actually turn.
# --------------------------------------------------------------------------

# Fallback signal mass point, used by the plain `default` model.
#
# The per-mass-point models derived at the bottom of this file override this via
# `cls_dict`, and the model body reads it off `self`. Keep it as a real point so
# that a bare `--inference-model default` still runs.
DEFAULT_SIGNAL_PROCESS = "azh_htt_zll_a1000_h600"

# Fallback signal-region observable.
#
# PLACEHOLDER. AN-2022/158 Sec. 7 fits templates binned in concentric ellipses
# in the 2D (pT(Z), dM) plane, unrolled to 1D. That variable does not exist in
# the config yet -- `pt_z_x_del_m` in azh/config/variables.py is a scalar
# product with placeholder binning, which is a different object and will give
# you different (worse) sensitivity. `del_m` is used here so the chain runs end
# to end today.
#
# The ellipses are re-derived per mass hypothesis, so once they exist this
# becomes mass-point dependent too. `_sr_variable()` below is already written
# to support that: give the derived models an `sr_variable` attribute and
# nothing else in this file has to change.
DEFAULT_SR_VARIABLE = "del_m"

# Observable in the WZ control region.
#
# The CR exists to constrain the WZ normalization (AN Sec. 8, ll. 618-632), not
# to discriminate signal, so a simple well-populated kinematic is the right
# choice and keeps the CR insensitive to the ellipse construction.
CR_VARIABLE = "pt_z"

# Processes to include, mapped to the datasets that build them.
#
# WHY EXPLICIT DATASETS INSTEAD OF THE AUTO-RESOLUTION LOOP:
# your colleague's model resolves datasets by walking the process tree
# (`walk_processes` + `dataset_inst.has_process`). That is fine when the
# inference processes are disjoint leaves, but your config registers BOTH `wz`
# AND `vv` in `process_names`, and `wz` is a child of `vv`. Auto-resolution
# would therefore assign `wz_pythia` to both the "WZ" and the "VV" entries and
# double count it in every bin. Listing datasets by hand makes the partition
# explicit and reviewable.
#
# NOTE: `ttz` and `ttw` are NOT currently in `process_names` in
# azh/config/config_run3.py -- only their parent `ttv` is. The guard in
# `_add_processes` below will tell you so by name. You need ttZ separable from
# ttW because AN Table 25 floats the ttZ normalization specifically, and
# bundling ttW into that rateParam would let the fit absorb ttW mismodelling
# into the ttZ yield. Add "ttz" and "ttw" to `process_names` before running.
PROCESS_DATASETS = {
    # ttZ -- the dominant irreducible background (AN Sec. 8, l. 604-608).
    "ttz": ["ttz_zll_m4to50_amcatnlo", "ttz_zll_m50toinf_amcatnlo"],
    # WZ+jets -- dominant in the 1b SR, normalization taken from the 0b CR.
    "wz": ["wz_pythia"],
    # ttbar. In a 3-lepton final state this enters via a nonprompt lepton.
    "tt": ["tt_sl_powheg", "tt_dl_powheg", "tt_fh_powheg"],
    # Remaining diboson (WW, ZZ) -- WZ deliberately excluded, see note above.
    "vv": ["ww_pythia", "zz_pythia"],
    "ttw": ["ttw_amcatnlo"],
    "tth": ["tth_hbb_powheg", "tth_hnonbb_powheg"],
    "st": [
        "st_tchannel_t_4f_powheg", "st_tchannel_tbar_4f_powheg",
        "st_twchannel_t_sl_powheg", "st_twchannel_tbar_sl_powheg",
        "st_twchannel_t_dl_powheg", "st_twchannel_tbar_dl_powheg",
    ],
    # Z+jets. This is the MC stand-in for what AN Sec. 8 estimates from data
    # with the fakeable-object method. Until that method exists in Run 3, these
    # two carry the nonprompt background and need a correspondingly generous
    # normalization uncertainty (see `_add_background_normalizations`).
    "dy_hf": ["dy_m50toinf_amcatnlo", "dy_m10to50_amcatnlo"],
    "dy_lf": ["dy_m50toinf_amcatnlo", "dy_m10to50_amcatnlo"],
    "w_lnu": ["w_lnu_amcatnlo"],
}

# Datasets with no LHEScaleWeight / LHEPdfWeight branch.
#
# config_run3.py tags the pythia dibosons `no_lhe_weights` and
# azh/selection/default.py skips the scale/PDF producers for them. So the
# `normalized_{mur,muf,murmuf_envelope,pdf}_weight` columns simply do not exist
# for those datasets, and asking for a scale/PDF shape nuisance on a process
# built from them yields an up variation identical to nominal -- a silently
# useless nuisance rather than an error. Keep this list in sync with the
# tagging block in config_run3.py.
NO_LHE_WEIGHT_PROCESSES = {"wz", "vv"}


def _signal_process(model) -> str:
    """
    The signal process this model instance is built for.

    Read off the instance rather than from a module constant, because
    `derive(..., cls_dict={"signal_process": ...})` attaches its entries as
    CLASS ATTRIBUTES of the derived model. `getattr` therefore picks up the
    override on a derived model and falls back to the module default on the
    plain `default` model, with no branching anywhere else in the file.
    """
    return getattr(model, "signal_process", DEFAULT_SIGNAL_PROCESS)


def _sr_variable(model) -> str:
    """
    The signal-region observable for this model instance.

    Same mechanism as above. Today every model returns the same placeholder;
    once the elliptical binning exists, the derive loop at the bottom of this
    file starts passing a per-mass-point variable name and this function is the
    only thing that needs to know.
    """
    return getattr(model, "sr_variable", DEFAULT_SR_VARIABLE)


def _era_key(config_inst) -> str:
    """
    Reproduce the era string used throughout config_run3.py: "2022preEE",
    "2022postEE", "2023preBPix", "2023postBPix", "2024".

    config_run3.py builds this as a local variable and never stores it on the
    config, so it has to be recomputed here. It is used to suffix the nuisances
    that AN Table 22 declares uncorrelated across years, so that four separate
    `cf.CreateDatacards` runs produce four distinct parameters.
    """
    campaign = config_inst.campaign
    year = campaign.x.year
    if year == 2022:
        return f"{year}{campaign.x.EE}EE"
    if year == 2023:
        return f"{year}{campaign.x.BPix}BPix"
    return str(year)


def _data_datasets(config_inst, flavor: str) -> list[str]:
    """
    Return the data primary datasets that supply the observation for a given Z
    flavor category.

    Resolved from tags rather than hard-coded era lists. config_run3.py tags
    every muon PD "mu" and every EGamma PD "egamma" (including the 2024 rename
    from `data_egamma_*` to `data_e_*`), so this automatically follows the era
    without a per-era lookup table that can drift.

    The split is required, not cosmetic: the analysis triggers are single
    lepton (HLT_IsoMu24 / HLT_Ele30_WPTight_Gsf) and `Trigger.applies_to_dataset`
    in azh/config/triggers.py gates each one on the corresponding tag. Feeding
    muon-PD data into a `2e` category would count events no electron trigger
    ever selected.

    `data_muoneg_*` is registered in the config but carries neither tag, so no
    trigger applies to it and it is correctly excluded here.
    """
    tag = "mu" if flavor == "2mu" else "egamma"
    return [
        dataset_inst.name
        for dataset_inst in config_inst.datasets
        if dataset_inst.is_data and dataset_inst.has_tag(tag)
    ]


@inference_model
def default(self):

    era = _era_key(self.config_inst)
    signal_process = _signal_process(self)
    sr_variable = _sr_variable(self)

    #
    # ------------------------------------------------------------------
    # CATEGORIES
    # ------------------------------------------------------------------
    #
    # Six datacard categories: 2 Z flavors x 3 regions. These are the
    # `3l__<flavor>__<region>` leaves built by azh/config/categories.py, i.e.
    # the ones that carry `catid_baseline` (Z window, pT_miss > 40, >=4 jets)
    # via their region categorizer. The `2l__*` validation categories are
    # deliberately NOT here -- they have no baseline cuts and exist for
    # Z-peak/lepton-calibration plots, not for the fit.
    #
    # Region definitions follow AN Table 16:
    #   wz_cr  : >=4 jets, 0 b tags  -> constrains the WZ normalization
    #   sr_1b  : >=4 jets, 1 b tag
    #   sr_2b  : >=4 jets, >=2 b tags
    #
    # `mc_stats=True` writes an `autoMCStats` line into the datacard, giving
    # each bin a nuisance for the finite size of the simulated samples. Turn it
    # off only if you have a specific reason; with 268 mass points and narrow
    # elliptical bins the MC statistical uncertainty is not negligible.

    for flavor in ["2e", "2mu"]:
        data_datasets = _data_datasets(self.config_inst, flavor)

        for region in ["sr_1b", "sr_2b", "wz_cr"]:
            self.add_category(
                # datacard-side name (appears as the combine bin label)
                f"cat_3l_{flavor}_{region}",
                # config-side name: must match a category built by
                # add_categories_regions() in azh/config/categories.py
                config_category=f"3l__{flavor}__{region}",
                config_variable=(CR_VARIABLE if region == "wz_cr" else sr_variable),
                config_data_datasets=data_datasets,
                mc_stats=True,
            )

    #
    # ------------------------------------------------------------------
    # PROCESSES
    # ------------------------------------------------------------------
    #

    # Signal first. `is_signal=True` is what makes combine put the process in
    # the <=0 column of the datacard and attach the signal strength mu to it.
    if not self.config_inst.has_process(signal_process):
        raise Exception(
            f"signal process '{signal_process}' is not registered in config "
            f"'{self.config_inst.name}'. Note config_2024 strips all azh_htt_zll_* "
            f"entries from process_names (no signal MC in that campaign), so run "
            f"with --configs run3_v12.",
        )
    self.add_process(
        "AZH",
        config_process=signal_process,
        config_mc_datasets=[signal_process],
        is_signal=True,
    )

    # Backgrounds.
    for proc, datasets in PROCESS_DATASETS.items():
        # Fail loudly and by name. The alternative -- silently skipping a
        # missing process -- produces a datacard that looks fine and is missing
        # a background, which you will not notice until the fit is pulled.
        if not self.config_inst.has_process(proc):
            raise Exception(
                f"process '{proc}' is not registered in config "
                f"'{self.config_inst.name}'; add it to `process_names` in "
                f"azh/config/config_run3.py",
            )
        # Same for datasets: an era that lacks one (e.g. ttw_amcatnlo is
        # currently only listed under the 2022 preEE block, and w_lnu_amcatnlo
        # is dropped for 2024) should be caught here rather than producing an
        # empty template.
        available = [d for d in datasets if self.config_inst.has_dataset(d)]
        if not available:
            raise Exception(
                f"process '{proc}' has none of its datasets {datasets} in config "
                f"'{self.config_inst.name}'",
            )

        # NOTE: newer columnflow supports `skip_if_empty=True` here, which drops
        # templates that come out empty in a given category instead of writing a
        # column of zeros. `process_spec` in your generation accepts only
        # (name, config_process, is_signal, config_mc_datasets, scale), so
        # passing it raises TypeError. If a background turns out to be empty in
        # some category, drop it from PROCESS_DATASETS by hand.
        self.add_process(
            proc,
            config_process=proc,
            config_mc_datasets=available,
        )

    #
    # ------------------------------------------------------------------
    # PARAMETER GROUPS
    # ------------------------------------------------------------------
    #
    # Groups are purely organisational but they matter downstream: combine's
    # impact and breakdown tooling can freeze a whole group at once, which is
    # how you produce the "systematics vs. statistical" split in the results
    # section.
    self.add_parameter_group("experiment")
    self.add_parameter_group("theory")
    self.add_parameter_group("background_norm")

    #
    # ------------------------------------------------------------------
    # LUMINOSITY  (AN Table 22, row "Luminosity")
    # ------------------------------------------------------------------
    #
    # This loop is taken from the columnflow template and works unmodified
    # because config_run3.py already builds `cfg.x.luminosity` as an
    # order.Number carrying named uncertainties -- `lumi_13p6TeV_correlated`
    # and `lumi_13p6TeV_uncorrelated_<year>` -- decomposed from the LUM POG
    # Run 3 covariance matrix.
    #
    # That decomposition is why this must stay a loop rather than a single
    # hard-coded lnN: the shared (vdM methodology) component and the year-local
    # component get separate nuisances, and collapsing them into one would
    # assert 100% correlation across years and inflate the combined result.
    # The names come straight from the config, so combineCards will correlate
    # the shared one across eras and keep the year-local ones separate,
    # automatically.
    #
    # `symmetrize` averages the up/down effects into one number, since combine
    # writes lnN as a single factor unless given an explicit asymmetric pair.
    lumi = self.config_inst.x.luminosity
    for unc_name in lumi.uncertainties:
        self.add_parameter(
            unc_name,
            type=ParameterType.rate_gauss,
            effect=lumi.get(names=unc_name, direction=("down", "up"), factor=True),
            transformations=[ParameterTransformation.symmetrize],
        )
        self.add_parameter_to_group(unc_name, "experiment")

    #
    # ------------------------------------------------------------------
    # EXPERIMENTAL SHAPE NUISANCES
    # ------------------------------------------------------------------
    #
    # Each entry maps a datacard nuisance name to a shift SOURCE registered in
    # config_run3.py (ll. 1246-1339). `config_shift_source="X"` makes
    # CreateDatacards look for the histograms filled under shifts "X_up" and
    # "X_down" and write them as the +-1 sigma templates.
    #
    # ONLY sources that are both registered AND actually varied appear here.
    # Three registered sources are deliberately absent:
    #
    #   top_pt  -- the shift exists, but `dataset.x.event_weights["top_pt_weight"]`
    #              is `[]`, so all_weights never declares it and the "up"
    #              histogram comes back bit-identical to nominal. The
    #              prescription is also unsettled (AN Sec. 9.1 l. 709 specifies
    #              a full-weight shape variation; gen_top.py currently does a
    #              flat x1.5 / x0.5, which is a pure rate effect).
    #   btag_*  -- the loop that registers these iterates over an empty
    #              `btag_uncs` list, so no such shift exists yet.
    #   tune, hdamp -- registered but tagged `disjoint_from_nominal`; they need
    #              dedicated alternative MC samples, which are not in the
    #              dataset list.
    #
    # Adding any of them now would produce a nuisance that is silently pinned
    # at nominal. CreateHistograms sets `missing_column_alias_strategy =
    # "original"`, so nothing warns you -- this is the exact failure mode
    # test_patch2.py was written to guard against.
    #
    # NAMING: these follow AN-2022/158 Table 22. Note the AN changelog (v8 ->
    # v10) records that the Run 2 nuisances were RENAMED to match the fully
    # hadronic channel's conventions for the combination. Your colleague's
    # hadronic model currently uses bare names ("mur", "muf"), so the two
    # channels are not yet consistent. Settle the convention with them before
    # anyone runs a combination -- mismatched names silently decorrelate
    # nuisances that should be shared.
    experimental_shapes = {
        # Lepton reco + ID (+iso) efficiency. AN Table 22 uses ONE nuisance per
        # flavor, correlated across years, hence no era suffix. config_run3.py
        # matches this: every electron SF column moves coherently under `e_sf`
        # and every muon SF column under `muon`.
        "CMS_eff_e": "e_sf",
        "CMS_eff_m": "muon",
        # Trigger efficiency. AN Table 22 has these uncorrelated across years.
        f"CMS_eff_e_trigger_{era}": "e_trig_sf",
        f"CMS_eff_m_trigger_{era}": "mu_trig_sf",
        # Pileup: minimum-bias cross section varied by ~+-4.6%
        # (AN Sec. 9.1 ll. 754-760). Uncorrelated across years.
        f"CMS_pileup_{era}": "minbias_xs",
        # JES. Currently the single "Total" source, because
        # `jec_uncertainty_sources = JEC_SOURCES_TOTAL` in config_run3.py.
        # AN Sec. 9.1 ll. 734-738 requires the 11-source reduced set (6
        # correlated across years, 5 not). When you switch to
        # JEC_SOURCES_REDUCED, replace this single entry with one parameter per
        # source and drop the era suffix from the six correlated ones.
        f"CMS_scale_j_Total_{era}": "jec_Total",
        # JER. AN Table 22: uncorrelated across years.
        f"CMS_res_j_{era}": "jer",
    }
    for param_name, shift_source in experimental_shapes.items():
        self.add_parameter(
            param_name,
            type=ParameterType.shape,
            config_shift_source=shift_source,
        )
        self.add_parameter_to_group(param_name, "experiment")

    #
    # ------------------------------------------------------------------
    # THEORY SHAPE NUISANCES  (AN Table 24)
    # ------------------------------------------------------------------
    #
    # Renormalization/factorization scale and PDF, applied PER PROCESS and
    # correlated across years.
    #
    # These are SHAPE-ONLY by construction. The columns entering the event
    # weight are `normalized_<unc>_weight`, produced by the
    # normalized_weight_factory in azh/production/weights.py, which divides
    # each weight by its per-process sum. So an up/down variation redistributes
    # events across the template without changing the process yield. That is
    # deliberate and matches AN Sec. 9.1 ll. 788-798: the normalization effect
    # is already covered by the inclusive cross-section rate nuisances, so
    # double counting it here would be wrong.
    #
    # Per-process rather than global because AN Table 24 declares
    # `CMS_mur_[process]` / `CMS_muf_[process]`: a scale variation on ttZ and
    # one on ttbar are independent theory uncertainties, not one shared
    # parameter.
    theory_processes = [
        p for p in ["AZH", *PROCESS_DATASETS]
        if p not in NO_LHE_WEIGHT_PROCESSES
    ]
    for proc in theory_processes:
        for unc in ["mur", "muf", "pdf"]:
            param_name = f"CMS_{unc}_{proc}"
            self.add_parameter(
                param_name,
                process=proc,
                type=ParameterType.shape,
                config_shift_source=unc,
            )
            self.add_parameter_to_group(param_name, "theory")

    #
    # ------------------------------------------------------------------
    # FLOATING BACKGROUND NORMALIZATIONS  (AN Table 25)
    # ------------------------------------------------------------------
    #
    # `rate_unconstrained` is the one ParameterType that does NOT go into the
    # tabular block of the datacard. The datacard writer routes it to
    # `blocks.line_parameters` and emits a `rateParam` line, i.e. a parameter
    # with no prior that the fit determines from the data.
    #
    # `effect=["1", "[0,2]"]` is the rateParam payload: starting value 1,
    # allowed range 0 to 2. Widen the range if a fit hits the boundary.
    #
    # ttZ (AN Sec. 8 ll. 611-613): floats freely in the SRs with no dedicated
    # control region. This works because the (pT(Z), dM) shape separates signal
    # from ttZ well enough for the fit to pin the normalization off the shape.
    # It is also why this must sit on ttZ alone and not on the `ttv` parent.
    self.add_parameter(
        "CMS_ttZ_norm",
        process="ttz",
        type=ParameterType.rate_unconstrained,
        effect=["1", "[0,2]"],
    )
    self.add_parameter_to_group("CMS_ttZ_norm", "background_norm")

    # WZ (AN Sec. 8 ll. 618-632): the same rateParam acts in the 0b CR and both
    # SRs simultaneously, so the high-statistics CR constrains it and the
    # constraint propagates into the SRs. Because no `category=` is given, the
    # parameter attaches to every category -- which is precisely the coupling
    # that makes the CR do its job. Do not scope it to the CR.
    #
    # AN ll. 630-632: correlated across years, because the dominant theory
    # uncertainty on the WZ n-jet distribution is not year dependent. With
    # per-era datacards that correlation is achieved by keeping this name free
    # of an era suffix so combineCards merges them.
    self.add_parameter(
        "CMS_WZ_norm_4j",
        process="wz",
        type=ParameterType.rate_unconstrained,
        effect=["1", "[0,2]"],
    )
    self.add_parameter_to_group("CMS_WZ_norm_4j", "background_norm")

    #
    # ------------------------------------------------------------------
    # NONPROMPT / Z+JETS NORMALIZATION  -- PLACEHOLDER
    # ------------------------------------------------------------------
    #
    # AN Sec. 9.1 ll. 701-708 assigns a conservative 30% normalization
    # uncertainty to the nonprompt background on top of the fake-factor
    # statistical and jet-flavor-composition uncertainties (AN Table 23:
    # CMS_fake_syst, CMS_fake_{e,m}_[year], CMS_fake_stat_{e,m}_[year]).
    #
    # Run 3 has no fakeable-object estimate yet, so nonprompt is carried by
    # MC Z+jets. A flat 30% here is a stand-in that keeps the fit from
    # over-trusting the MC, NOT an implementation of the AN's method. For
    # scale: in AN Table 17 the Fakes column is 530.3 of 3523.4 total
    # background at preselection, about 15%, so this is not a small effect and
    # the placeholder should not survive to an unblinding request.
    for proc in ["dy_hf", "dy_lf"]:
        param_name = f"CMS_nonprompt_norm_{proc}"
        self.add_parameter(
            param_name,
            process=proc,
            type=ParameterType.rate_gauss,
            effect=1.30,
        )
        self.add_parameter_to_group(param_name, "background_norm")

    #
    # ------------------------------------------------------------------
    # POST-PROCESSING
    # ------------------------------------------------------------------
    #
    # Drops parameters that ended up attached to no process or category (for
    # instance a shape nuisance on a process that is not in PROCESS_DATASETS).
    # Without it those leave dangling columns that combine rejects.
    #
    # Strictly this call is redundant: `InferenceModel.__init__` already runs
    # `self.cleanup()` immediately after `init_func()`. It is kept because it is
    # idempotent, it matches the convention in the hadronic model, and it makes
    # the intent explicit at the point where the model is finished.
    self.cleanup()


#
# --------------------------------------------------------------------------
# PER-MASS-POINT MODELS
# --------------------------------------------------------------------------
#
# AN-2022/158 Sec. 7 performs a separate fit per (mA, mH) hypothesis, so the
# analysis needs one inference model per mass point, not one model that knows
# about all of them. The loop below creates all 262 at import time.
#
# HOW THIS WORKS
# `derive` builds a subclass of `default` with the same `init_func` body but a
# different name, attaching `cls_dict` entries as class attributes -- which is
# what `_signal_process()` / `_sr_variable()` read. Every derived class is
# registered in the `_subclasses` registry of the base class, and
# `InferenceModelMixin.get_inference_model_inst` resolves `--inference-model X`
# through `InferenceModel.get_cls(X)`. That lookup only searches classes that
# already exist, which is why these have to be created at MODULE IMPORT time
# rather than on demand. law imports this module because it is listed under
# `inference_modules` in law.cfg.
#
# Creating 262 classes is cheap -- `derive` only calls the metaclass, it does
# not run the model body. The body runs once per instantiation, i.e. once per
# task, for the one model actually requested.
#
# STORE PATHS
# `InferenceModelMixin.store_parts` inserts `inf__<model name>` before the
# version directory, so each mass point automatically gets its own output tree
# and they cannot overwrite each other:
#
#   .../cf.CreateDatacards/<config>/inf__azh_a1000_h600/<version>/
#
# NAMING
# `azh_a<mA>_h<mH>` -- the cmsdb `_htt_zll` infix is dropped because it is
# constant across the grid and only makes the store paths longer. The name is
# reversible, which matters when a downstream limit scan has to recover the
# mass point from a directory listing.
for _signal in AZH_SIGNAL_PROCESSES:
    _m_a, _m_h = masses(_signal)
    default.derive(
        f"azh_a{_m_a}_h{_m_h}",
        cls_dict={
            "signal_process": _signal,
            # Once the elliptical binning exists, add the per-mass-point
            # observable here, e.g.
            #   "sr_variable": f"ellipse_a{_m_a}_h{_m_h}",
            # and register the matching variable in azh/config/variables.py.
            # Nothing else in this file changes.
        },
    )
