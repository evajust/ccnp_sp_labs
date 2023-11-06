#!/usr/bin/env python3
from argparse import ArgumentParser
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_utils.plugins.tasks.data import load_yaml
from nornir_jinja2.plugins.tasks import template_file
from nornir_scrapli.tasks import (
    netconf_edit_config,
    netconf_commit,
    netconf_lock,
    netconf_unlock,
)


def get_args():
    parser = ArgumentParser()
    parser.add_argument('--lab', type=str, required=True,
                        help="Name of the lab to configure.")
    return parser.parse_args()


def set_config(lab):
    """
    This takes the place of the standard config.yaml file.  This way,
    a variable can be used for the directory of the hosts file.
    """
    return {
        "inventory": {
            "plugin": "SimpleInventory",
            "options": {
                "host_file": f"{lab}/scrapli/hosts.yaml",
                "group_file": f"{lab}/scrapli/groups.yaml"}},
        "runner": {
            "plugin": "threaded",
            "options": {
                "num_workers": 10}}}


def load_vars(task, lab):
    """
    Load host variables and bind them to the per-host dict key "facts".
    """

    data = task.run(
            task=load_yaml,
            name=f"Loading variables for {task.host}",
            file=f"{lab}/scrapli/{task.host}.yaml",
    )
    task.host["facts"] = data.result


def lock_config(task):
    task.run(task=netconf_lock, target="candidate", name="Locking...")


def build_config(task, lab):
    device_template = task.run(
            task=template_file,
            name=f"Building device config for {task.host}",
            template=f"{lab}/scrapli/{task.host}.jinja",
            path="./",
            )
    device_config = device_template.result
    task.run(
            task=netconf_edit_config,
            name="Automating Deployment",
            target="candidate",
            config=device_config,
            )


def commit_configs(task):
    """
    Commit the configuration changes.
    """
    task.run(
        task=netconf_commit,
        name=f"Committing Changes for {task.host}"
    )


def unlock_config(task):
    task.run(task=netconf_unlock, target="candidate")


def main():
    args = get_args()
    lab = args.lab
    nr = InitNornir(**set_config(lab))
    var = nr.run(task=load_vars, lab=lab)
    print_result(var)
    lock_result = nr.run(task=lock_config, name="NETCONF Lock")
    print_result(lock_result)
    config_build_results = nr.run(task=build_config, lab=lab, name="Config Build")
    print_result(config_build_results)
    commit_results = nr.run(task=commit_configs, name="NETCONF Commit")
    print_result(commit_results)
    unlock_result = nr.run(task=unlock_config, name="NETCONF Unlock")
    print_result(unlock_result)


if __name__ == "__main__":
    main()
