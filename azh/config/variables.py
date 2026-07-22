# coding: utf-8

"""
Definition of variables.
"""

import order as od

from columnflow.util import maybe_import
from columnflow.columnar_util import EMPTY_FLOAT

np = maybe_import("numpy")
ak = maybe_import("awkward")


def add_feature_variables(config: od.Config) -> None:
    """
    Adds variables to a *config* that are produced as part of the `features` producer.
    """

    # Event properties
    config.add_variable(
        name="n_jet",
        binning=(12, -0.5, 11.5),
        x_title="Number of jets",
        discrete_x=True,
    )

    # jj features
    config.add_variable(
        name="deltaR_jj",
        binning=(40, 0, 5),
        x_title=r"$\Delta R(j_{1},j_{2})$",
    )


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
        binning=(51, -.5, 50.5),
        x_title="Number of primary vertices",
        discrete_x=True,
    )

    #
    # Object properties
    #

    config.add_variable(
        name="jets_pt",
        expression="Jet.pt",
        binning=(40, 0, 400),
        unit="GeV",
        x_title="$p_{T}$ of all jets",
    )

    config.add_variable(
        name="n_jets",
        expression="n_jets",
        binning=(12, -0.5, 11.5),
        unit="GeV",
        x_title="Number of jets",
    )

    config.add_variable(
        name="n_bjets",
        expression="n_bjets",
        binning=(5, -0.5, 4.5),
        unit="GeV",
        x_title="Number of bjets",
    )

    config.add_variable(
        name="jets_btag",
        expression="Jet.btagDeepFlavB",
        binning=(20, 0, 1),
        unit="",
        x_title="Btag Score Deep Jet",
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
        name="m_h",
        expression="m_h",
        binning=(50, 0, 2500),
        unit="GeV",
        x_title="Invariant mass of the reconstructed H",
    )
    config.add_variable(
        name="m_a",
        expression="m_a",
        binning=(40, 0, 2000),
        unit="GeV",
        x_title="Invariant mass of the reconstructed A",
    )
    config.add_variable(
        name="del_m",
        expression="del_m",
        binning=(40, 0, 2000),
        unit="GeV",
        x_title="Mass difference between H and A",
    )
    config.add_variable(
        name="pt_z",
        expression="pt_z",
        binning=(10, 0, 700),
        unit="GeV",
        x_title="Transverse momentum of Z boson",
    )

    # pt_z x del_m product feature (callable expression -> declare its input
    # columns via aux["inputs"], otherwise the plotting task loads neither).
    # del_m is sentineled to -1 outside the >=4-jet reco (see higgs_reco.py),
    # so those events give a negative product and fall in the underflow.
    # NOTE: binning is a placeholder -- retune once you see the distribution.
    config.add_variable(
        name="pt_z_x_del_m",
        expression=lambda events: events.pt_z * events.del_m,
        aux={"inputs": {"pt_z", "del_m"}},
        null_value=EMPTY_FLOAT,
        binning=(40, 0.0, 700000.0),
        unit=r"GeV$^{2}$",
        x_title=r"$p_{T}^{Z} \times \Delta m$",
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
        name="delta_b_z",
        expression="delta_b_z",
        binning=(50, 0, 10),
        unit="",
        x_title="Distance between b and Z",
    )

    config.add_variable(
        name="PNN_output",
        expression="PNN.output",
        binning=(10, 0, 1),
        unit="",
        x_title="PNN output score",
    )
    config.add_variable(
        name="MET",
        expression="MET.pt",
        binning=(20, 0, 400),
        unit="",
        x_title="MET $p_{T}$",
    )

    config.add_variable(
        name="category_ids",
        expression="category_ids",
        binning=(20, 0, 100000),
        unit="",
        x_title="Event category",
    )
    config.add_variable(
        name="deltaPhi_MET_Jet1",
        expression="deltaPhi_MET_Jet1",
        binning=(40, -3.2, 3.2),
        unit="",
        x_title="$\Delta \phi$ (MET,Jet1) ",
    )
    config.add_variable(
        name="deltaPhi_MET_Jet2",
        expression="deltaPhi_MET_Jet2",
        binning=(40, -3.2, 3.2),
        unit="",
        x_title="$\Delta \phi$ (MET,Jet2) ",
    )
    config.add_variable(
        name="deltaPhi_MET_Jet3",
        expression="deltaPhi_MET_Jet3",
        binning=(40, -3.2, 3.2),
        unit="",
        x_title="$\Delta \phi$ (MET,Jet3) ",
    )
    # Jets (3 pt-leading jets)
    for i in range(6):
        config.add_variable(
            name=f"jet{i+1}_pt",
            expression=f"Jet.pt[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(40, 0., 400.),
            unit="GeV",
            x_title=r"Jet %i $p_{T}$" % (i + 1),
        )
        config.add_variable(
            name=f"jet{i+1}_eta",
            expression=f"Jet.eta[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(50, -2.5, 2.5),
            x_title=r"Jet %i $\eta$" % (i + 1),
        )
        config.add_variable(
            name=f"jet{i+1}_phi",
            expression=f"Jet.phi[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(40, -3.2, 3.2),
            x_title=r"Jet %i $\phi$" % (i + 1),
        )
        config.add_variable(
            name=f"jet{i+1}_mass",
            expression=f"Jet.mass[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(40, 0, 200),
            unit="GeV",
            x_title=r"Jet %i mass" % (i + 1),
        )

    for i in range(2):
        config.add_variable(
            name=f"Lepton{i+1}_pt",
            expression=f"Leptons.pt[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(40, 0., 400.),
            unit="GeV",
            x_title=r"Lepton %i $p_{T}$" % (i + 1),
        )
        config.add_variable(
            name=f"Lepton{i+1}_eta",
            expression=f"Leptons.eta[:,{i}]",
            null_value=EMPTY_FLOAT,
            binning=(50, -2.5, 2.5),
            x_title=r"Lepton %i $\eta$" % (i + 1),
        )
        config.add_variable(
            name=f"Lepton{i+1}_phi",
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
        x_title=r"Number of jets ($p_{T}$ > 30 GeV, $|\eta| < 2.4$)",
    )
    config.add_variable(
        name="cf_n_bjet",
        expression="cutflow.n_bjet",
        binning=(11, -0.5, 10.5),
        x_title=r"Number of b-taggeg jets ($p_{T}$ > 30 GeV, $|\eta| < 2.4$)",
    )
    config.add_variable(
        name="n_jet_loose",
        expression="cutflow.n_jet_loose",
        binning=(12, -0.5, 11.5),
        x_title=r"Number of jets ($p_{T}$ > 15 GeV, $|\eta| < 4.7$)",
        discrete_x=True,
    )
    config.add_variable(
        name="cf_n_jet_loose",
        expression="cutflow.n_jet_loose",
        binning=(12, -0.5, 11.5),
        x_title=r"Number of jets ($p_{T}$ > 15 GeV, $|\eta| < 4.7$)",
        discrete_x=True,
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
        expression="cutflow.n_muo",
        binning=(5, -0.5, 4.5),
        x_title=r"Number of muons ($p_{T}$ > 20 GeV, $|\eta| < 2.4$ + tight Id)",
    )
    config.add_variable(
        name="cf_n_muo_loose",
        expression="cutflow.n_muo_tight",
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
        binning=(40, 0., 400.),
        unit="GeV",
        x_title=rf"lepton {i + 1} $p_{{T}}$",
    )
    config.add_variable(
        name=f"cf_lep{i + 1}_eta",
        expression=f"cutflow.lep{i + 1}_eta",
        binning=(50, -2.5, 2.5),
        x_title=rf"lepton {i + 1} $\eta$",
    )

    for i in range(4):
        config.add_variable(
            name=f"cf_jet{i+1}_pt",
            expression=f"cutflow.jet{i+1}_pt",
            binning=(40, 0., 400.),
            unit="GeV",
            x_title=rf"jet {i+1} $p_{{T}}$",
        )

        config.add_variable(
            name=f"cf_jet{i+1}_eta",
            expression=f"cutflow.jet{i+1}_eta",
            binning=(50, -2.5, 2.5),
            x_title=rf"jet {i+1} $\eta$",
        )
    
    # Trigger descision
    config.add_variable(
        name="trig_ids",
        expression="trig_ids",
        binning=(21, -0.5, 20.5),
        unit="",
        x_title="Trigger IDs",
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
