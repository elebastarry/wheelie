#!/usr/bin/env python3

import time
import getpass
import argparse
from pathlib import Path

from plumbum import SshMachine
from plumbum import local
from plumbum import FG


parser = argparse.ArgumentParser(description='Send and install wheel on remote machine')
parser.add_argument('hostname', type=str, help='the hostname of the server')
parser.add_argument('venv', type=str, help='the name of the virtualenv', default=getpass.getuser())

args = parser.parse_args()

start_time = time.time()
print("Building wheel")
local["make"]["clean"]()
local["make"]["wheel"]()

PIP_PATH = Path("bin/pip")

print(f"Connecting to {args.hostname}")
remote = SshMachine(args.hostname)
venv_path =  Path("/etc/virtualenvs") / args.venv

with remote.env(PIP_INDEX_URL=local.env["ARTIFACTORY_URL"]), remote.tempdir() as temp:
    wheel = next(file for file in local.path("dist").list() if file.name.endswith("whl"))
    print(f"Uploading {wheel} to {args.hostname}")
    remote.upload(wheel, temp)
    venv_exists = remote.path(venv_path).exists()
    if not venv_exists:
        print(f"No venv found at {venv_path}, creating venv")
        remote.path(venv_path).mkdir()
        remote["python3"]["-m"]["venv"][venv_path]()
    pip_command = remote[str(venv_path / PIP_PATH)]["install"][str(temp / wheel.name)]["--force-reinstall"]
    if venv_exists:
        pip_command = pip_command["--no-deps"]
    print(f"Running {pip_command} on {args.hostname}")
    pip_command & FG

print(f"Completed installation in {time.time() - start_time}s")
