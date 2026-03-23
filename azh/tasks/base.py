# coding: utf-8

"""
Custom base tasks.
"""

from columnflow.tasks.framework.base import BaseTask


class AZHTask(BaseTask):

    task_namespace = "azh"


import os
import law
from columnflow.tasks.framework.remote import HTCondorWorkflow


def _htcondor_output_directory_afs(self):
    """
    Override to use CF_JOB_BASE on AFS instead of EOS store,
    since standard CERN bigbird schedds reject EOS paths in initialdir.
    """
    job_base = os.environ.get("CF_JOB_BASE", "/afs/cern.ch/user/e/eranders/azh_jobs")
    # use the task's law-generated job file directory which is already unique
    return law.LocalDirectoryTarget(os.path.join(job_base, "htcondor_out"))


# patch columnflow's HTCondorWorkflow so all cf.* tasks use AFS for initialdir
HTCondorWorkflow.htcondor_output_directory = _htcondor_output_directory_afs
