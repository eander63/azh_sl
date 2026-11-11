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
    # one directory PER TASK: job records (htcondor_jobs_<range>.json) and job
    # logs are named only by branch range, so a shared directory made workflows
    # with equal branch counts overwrite each other's records and logs
    return law.LocalDirectoryTarget(os.path.join(job_base, "htcondor_out", self.task_family, self.live_task_id))


# patch columnflow's HTCondorWorkflow so all cf.* tasks use AFS for initialdir
HTCondorWorkflow.htcondor_output_directory = _htcondor_output_directory_afs
