"""
Definition of variables.
"""

import order as od
from columnflow.columnar_util import EMPTY_FLOAT
from columnflow.util import maybe_import

np = maybe_import("numpy")
ak = maybe_import("awkward")


def add_variables(config: od.Config) -> None:
    """
    Adds all variables to a *config* that are present after `ReduceEvents`
    without calling any producer
    """

    # (the "event", "run" and "lumi" variables are required for some cutflow plotting task,
    # and also correspond to the minimal set of columns that coffea's nano scheme requires)
    config.add_variable(
        name="event",
        expression="event",
        binning=(1, 0.0, 1.0e9),
        x_title="Event number",
        discrete_x=True,
    )
    config.add_variable(
        name="run",
        expression="run",
        binning=(1, 100000.0, 500000.0),
        x_title="Run number",
        discrete_x=True,
    )
    config.add_variable(
        name="lumi",
        expression="luminosityBlock",
        binning=(1, 0.0, 5000.0),
        x_title="Luminosity block",
        discrete_x=True,
    )

    #
    # Weights
    #

    # TODO: implement tags in columnflow; meanwhile leave these variables commented out (as they only work for mc)
    config.add_variable(
        name="npvs",
        expression="PV.npvs",
        binning=(51, -0.5, 50.5),
        x_title="Number of primary vertices",
        discrete_x=True,
    )

    #
    # Object properties
    #

    config.add_variable(
        name="jets_pt",
        expression="AnaJet.pt",
        binning=(40, 0, 400),
        unit="GeV",
        x_title="$p_{T}$ of all jets",
    )



    # discriminator column is era-dependent: ParticleNet (2022/23) vs UParT (2024)
    _btag = config.x.btag_default
    config.add_variable(
        name="jets_btag",
        expression="AnaJet.btag",
        binning=(20, 0, 1),
        unit="",
        x_title=f"b tag score ({_btag.name})",
    )

    config.add_variable(
        name="m_z",
        expression="m_z",
        binning=(60, 60.0, 120.0),
        unit="GeV",
        x_title=r"$m_{\ell\ell}$ [GeV]",
    )
    config.add_variable(
        name="m_z_wide",
        expression="m_z",
        binning=(40, 0.0, 400.0),
        unit="GeV",
        x_title=r"$m_{\ell\ell}$ [GeV] (wide)",
    )
    config.add_variable(
        name="pt_z",
        expression="pt_z",
        binning=(10, 0, 700),
        unit="GeV",
        x_title="Transverse momentum of Z boson",
    )

    config.add_variable(
        name="m_z_fine",
        expression="m_z",
        binning=(100, 80.0, 100.0),
        unit="GeV",
        x_title=r"$m_{\ell\ell}$ [GeV]",
    )

    config.add_variable(
        name="pt_z_fine",
        expression="pt_z",
        binning=(100, 0.0, 100.0),
        unit="GeV",
        x_title=r"$p_{T}^{Z}$ [GeV]",
    )


    config.add_variable(
        name="PuppiMET",
        expression="PuppiMET.pt",
        binning=(20, 0, 400),
        unit="",
        x_title="PuppiMET $p_{T}$",
    )

    config.add_variable(
        name="category_ids",
        expression="category_ids",
        binning=(20, 0, 100000),
        unit="",
        x_title="Event category",
    )
    # analysis jet counts (production/jets.py; follow the JES/JER shifts)
    config.add_variable(
        name="n_jet",
        expression="n_jet",
        binning=(12, -0.5, 11.5),
        x_title=r"Number of jets ($p_{T}$ > 30 GeV, $|\eta| < 2.5$)",
        discrete_x=True,
    )
    config.add_variable(
        name="n_bjet",
        expression="n_bjet",
        binning=(6, -0.5, 5.5),
        x_title=r"Number of b-tagged jets (medium WP)",
        discrete_x=True,
    )
    # analysis jets (AnaJet, pT-ordered)
    for i in range(6):
        config.add_variable(
            name=f"jet{i + 1}_pt",
            expression=f"AnaJet.pt[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(40, 0.0, 400.0),
            unit="GeV",
            x_title=r"Jet %i $p_{T}$" % (i + 1),
        )
        config.add_variable(
            name=f"jet{i + 1}_eta",
            expression=f"AnaJet.eta[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(50, -2.5, 2.5),
            x_title=r"Jet %i $\eta$" % (i + 1),
        )
        config.add_variable(
            name=f"jet{i + 1}_phi",
            expression=f"AnaJet.phi[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(40, -3.2, 3.2),
            x_title=r"Jet %i $\phi$" % (i + 1),
        )
        config.add_variable(
            name=f"jet{i + 1}_mass",
            expression=f"AnaJet.mass[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(40, 0, 200),
            unit="GeV",
            x_title=r"Jet %i mass" % (i + 1),
        )

    for i in range(2):
        config.add_variable(
            name=f"Lepton{i + 1}_pt",
            expression=f"Leptons.pt[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(40, 0.0, 400.0),
            unit="GeV",
            x_title=r"Lepton %i $p_{T}$" % (i + 1),
        )
        config.add_variable(
            name=f"Lepton{i + 1}_eta",
            expression=f"Leptons.eta[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(50, -2.5, 2.5),
            x_title=r"Lepton %i $\eta$" % (i + 1),
        )
        config.add_variable(
            name=f"Lepton{i + 1}_phi",
            expression=f"Leptons.phi[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(40, -3.2, 3.2),
            x_title=r"Lepton %i $\phi$" % (i + 1),
        )

    # Cutflow Variables
    config.add_variable(
        name="cf_n_jet",
        expression="cutflow.n_jet",
        binning=(11, -0.5, 10.5),
        x_title=r"Number of jets ($p_{T}$ > 30 GeV, $|\eta| < 2.5$)",
    )
    config.add_variable(
        name="cf_n_bjet",
        expression="cutflow.n_bjet",
        binning=(11, -0.5, 10.5),
        x_title=r"Number of b-tagged jets ($p_{T}$ > 30 GeV, $|\eta| < 2.5$)",
    )
    config.add_variable(
        name="cf_n_ele",
        expression="cutflow.n_ele_tight",
        binning=(5, -0.5, 4.5),
        x_title=r"Number of electrons ($p_{T}$ > 10 GeV, $|\eta| < 2.5$, WP80)",
    )
    config.add_variable(
        name="cf_n_ele_loose",
        expression="cutflow.n_ele_loose",
        binning=(5, -0.5, 4.5),
        x_title=r"Number of loose electrons ($p_{T}$ > 10 GeV, $|\eta| < 2.4$ + loose Iso) ",
    )
    config.add_variable(
        name="cf_n_muo",
        expression="cutflow.n_muo_tight",
        binning=(5, -0.5, 4.5),
        x_title=r"Number of muons ($p_{T}$ > 20 GeV, $|\eta| < 2.4$ + tight Id)",
    )
    config.add_variable(
        name="cf_n_muo_loose",
        expression="cutflow.n_muo_loose",
        binning=(5, -0.5, 4.5),
        x_title=r"Number of muons ($p_{T}$ > 10 GeV, $|\eta| < 2.4$, tightId + iso < 0.15)",
    )
    config.add_variable(
        name="cf_n_lep_loose",
        expression="cutflow.n_lep_loose",
        binning=(6, -0.5, 5.5),
        x_title=r"Number of loose leptons ($p_{T}$ > 10 GeV)",
    )

    for i in range(3):
        config.add_variable(
            name=f"cf_lep{i + 1}_pt",
            expression=f"cutflow.lep{i + 1}_pt",
            binning=(40, 0.0, 400.0),
            unit="GeV",
            x_title=rf"lepton {i + 1} $p_{{T}}$",
        )
        config.add_variable(
            name=f"cf_lep{i + 1}_eta",
            expression=f"cutflow.lep{i + 1}_eta",
            binning=(50, -2.5, 2.5),
            x_title=rf"lepton {i + 1} $\eta$",
        )

    # ── 3-lepton variables ──
    config.add_variable(
        name="n_tight_leptons",
        expression="n_tight_leptons",
        binning=(7, -0.5, 6.5),
        x_title="Number of tight leptons ($p_{T} > 10$ GeV)",
        discrete_x=True,
    )
    config.add_variable(
        name="min_mll",
        expression="min_mll",
        binning=(50, 0, 200),
        unit="GeV",
        x_title=r"Min($m_{\ell\ell}$) [GeV]",
    )
    config.add_variable(
        name="charge_sum",
        expression="charge_sum",
        binning=(7, -3.5, 3.5),
        x_title=r"$\sum q_{\ell}$",
        discrete_x=True,
    )
    config.add_variable(
        name="w_lepton_pt",
        expression="w_lepton_pt",
        binning=(40, 0, 200),
        unit="GeV",
        x_title=r"W lepton $p_{T}$ [GeV]",
    )
