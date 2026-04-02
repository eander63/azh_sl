import law
import order as od

from columnflow.util import maybe_import
from columnflow.production import producer, Producer
from columnflow.production.processes import process_ids
from columnflow.columnar_util import set_ak_column

np = maybe_import("numpy")
ak = maybe_import("awkward")

def get_process_id_from_masks(
    events: ak.Array,
    process_masks: dict[str, ak.Array],
    dataset_inst: od.Dataset,
) -> ak.Array:
    """
    Assigns a process ID to each event based on the masks in *process_masks*.

    :raises NotImplementedError: If the events are assigned to a process that are not registered as leaf processes
    :raises ValueError: If the events have overlapping processes or if some events have not been assigned a process
    """
    leaf_procs = dataset_inst.get_leaf_processes()

    process_id = ak.Array(np.zeros(len(events)).astype(np.int32))
    for proc_name, mask in process_masks.items():
        if ak.any(mask):
            if not dataset_inst.has_process(proc_name):
                raise NotImplementedError(
                    f"Events from dataset {dataset_inst.name} are assigned process {proc_name} "
                    f"but dataset has only {leaf_procs} registered as leaf processes",
                )
            proc_id = dataset_inst.get_process(proc_name).id

            if not ak.all(process_id[mask] == 0):
                raise ValueError(f"Events from dataset {dataset_inst.name} have overlapping processes")

            process_id = ak.where(mask, proc_id, process_id)

    if ak.any(process_id == 0):
        raise ValueError(f"Events from dataset {dataset_inst.name} have not been assigned any process")

    return process_id


@producer(
    uses={"GenJet.{pt,eta,hadronFlavour}"},
    produces={"process_id"},
)
def dy_producer(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    This function calculates the process ID for the given Drell-Yan dataset based on the
    number of partons and hadron flavor.

    :raises NotImplementedError: If the dataset cannot be assigned to the correct DY base process
    """
    # n_partons = events.LHE.NpNLO

    genjet_mask = (events.GenJet["pt"] >= 20) & (abs(events.GenJet["eta"]) < 2.4)
    genjet = (events.GenJet[genjet_mask])
    hf_genjet_mask = (genjet.hadronFlavour == 4) | (genjet.hadronFlavour == 5)
    is_hf = ak.any(hf_genjet_mask, axis=1)

    # hf_genjets = genjet[hf_genjet_mask]
    # hf_genjets = hf_genjets[ak.num(hf_genjets, axis=1) >= 1]
    # from IPython import embed; embed()
    # identify base process as "dy_{mass-window}"
    base_proc_name = "_".join(self.dataset_inst.name.split("_")[:2])
    # print(base_proc_name)
    if base_proc_name == "dy_m50toinf" and "amcatnlo" in self.dataset_inst.name and not any(f"{n}j" in self.dataset_inst.name for n in range(5)):
        # inclusive amcatnlo sample - split by gen jet multiplicity and hf/lf
        n_genjet = ak.num(genjet, axis=1)
        process_masks = {
            f"{base_proc_name}_0j_hf": ((n_genjet == 0) & is_hf),
            f"{base_proc_name}_0j_lf": ((n_genjet == 0) & ~is_hf),
            f"{base_proc_name}_1j_hf": ((n_genjet == 1) & is_hf),
            f"{base_proc_name}_1j_lf": ((n_genjet == 1) & ~is_hf),
            f"{base_proc_name}_2j_hf": ((n_genjet == 2) & is_hf),
            f"{base_proc_name}_2j_lf": ((n_genjet == 2) & ~is_hf),
            f"{base_proc_name}_3j_hf": ((n_genjet >= 3) & is_hf),
            f"{base_proc_name}_3j_lf": ((n_genjet >= 3) & ~is_hf),
        }
    elif base_proc_name == "dy_m50toinf":
        # separate into njet and hf/lf
        process_masks = {
            f"{base_proc_name}_0j_hf": ((str(0)+"j" in self.dataset_inst.name) & is_hf),
            f"{base_proc_name}_1j_hf": ((str(1)+"j" in self.dataset_inst.name) & is_hf),
            f"{base_proc_name}_2j_hf": ((str(2)+"j" in self.dataset_inst.name) & is_hf),
            f"{base_proc_name}_3j_hf": ((str(3)+"j" in self.dataset_inst.name) & is_hf),  
            f"{base_proc_name}_4j_hf": ((str(4)+"j" in self.dataset_inst.name) & is_hf), 
            f"{base_proc_name}_0j_lf": ((str(0)+"j" in self.dataset_inst.name) & ~is_hf),
            f"{base_proc_name}_1j_lf": ((str(1)+"j" in self.dataset_inst.name) & ~is_hf),
            f"{base_proc_name}_2j_lf": ((str(2)+"j" in self.dataset_inst.name) & ~is_hf),
            f"{base_proc_name}_3j_lf": ((str(3)+"j" in self.dataset_inst.name) & ~is_hf), 
            f"{base_proc_name}_4j_lf": ((str(4)+"j" in self.dataset_inst.name) & ~is_hf), 
        }
    elif base_proc_name == "dy_m4to10" or base_proc_name == "dy_m10to50":
        # separate into hf/lf
        process_masks = {
            f"{base_proc_name}_hf": is_hf,
            f"{base_proc_name}_lf": ~is_hf,
        }
    else:
        raise NotImplementedError(
            f"Process Producer {self.cls_name} for dataset {self.dataset_inst.name} not implemented",
        )

    process_id = get_process_id_from_masks(events, process_masks, self.dataset_inst)
    events = set_ak_column(events, "process_id", process_id, value_type=np.int32)

    return events