import sys
import logging

logging.basicConfig(
    format='%(asctime)s [%(levelname)s]: %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stdout,
    level=logging.INFO,
)

log = logging.getLogger(__name__)

import os
import subprocess

import pathlib
import json
import time
import shutil
import io

import argparse

# https://www.freedesktop.org/wiki/Specifications/DiscoverablePartitionsSpec/
UUID_SWAP = "0657fd6d-a4ab-43c4-84e5-0933c84b4f4f"
UUID_BIOS = "21686148-6449-6e6f-744e-656564454649"
UUID_OTHER = "0fc63daf-8483-4772-8e79-3d69d8477de4"

INSTALL_DIR_PREFIX = "/mnt/installer"

class FullPaths(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))


def is_block_device(dirname: str) -> str:
    p = pathlib.Path(dirname).resolve()

    if not p.is_block_device():
        msg = "'{0}' is not a block device.".format(dirname)
        raise argparse.ArgumentTypeError(msg)
    else:
        return dirname


def get_block_device(device: str) -> dict:
    run = ["lsblk", "-O", "-J", device]
    log.info("Running {}".format(" ".join(run)))
    lsblk_run = subprocess.run(run, timeout=30, check=True, stdout=subprocess.PIPE)

    data = json.loads(lsblk_run.stdout)

    if 'blockdevices' not in data:
        raise KeyError("Key 'blockdevices' not found!")

    data = data['blockdevices']

    if len(data) == 0:
        raise IndexError("No data found")

    if len(data) != 1:
        raise IndexError("Too many devices??")

    return data[0]


def sgdisk(device, parameters: list):
    if not isinstance(parameters, list):
        raise TypeError("Wrong type: {}".format(type(parameters)))

    if len(parameters) == 0:
        raise ValueError("No parameters given.")

    run = ["sgdisk"]
    run.extend(parameters)
    run.append(device)

    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)


def partprobe(device):
    run = ["partprobe"]
    run.append(device)

    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)


def fdisk(device, parameters: list):
    if not isinstance(parameters, list):
        raise TypeError("Wrong type: {}".format(type(parameters)))

    if len(parameters) == 0:
        raise ValueError("No parameters given.")

    run = ["fdisk"]
    run.extend(parameters)
    run.append(device)

    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)


def wipefs(device, parameters: list):
    if not isinstance(parameters, list):
        raise TypeError("Wrong type: {}".format(type(parameters)))

    if len(parameters) == 0:
        raise ValueError("No parameters given.")

    run = ["wipefs"]
    run.extend(parameters)
    run.append(device)

    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)


def mkswap(device):
    run = ["mkswap", device]
    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)


def swapon(device):
    run = ["swapon", device]
    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)


def enable_swap(device):
    mkswap(device)
    swapon(device)


def mount(device, destination):
    run = ["mount", device, destination]
    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)

def unmount(device):
    run = ["umount", device]
    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)

def mkfs_ext4(device):
    run = ["mkfs.ext4", device]
    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)

def rankmirrors(file, count=5):
    run = ["rankmirrors", "-n", str(count), file]
    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)

def pacstrap(install_dir, files:list):
    run = ["pacstrap"]
    run.append(install_dir)
    run.extend(files)
    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)

def genfstab(install_dir):
    run = ["genfstab", "-U", install_dir]
    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)

def chroot(install_dir):
    run = ["arch-chroot", install_dir]
    log.debug("Running {}".format(" ".join(run)))
    return subprocess.run(run, check=True, stdout=subprocess.PIPE)

def unmount_all(device):
    block_device = get_block_device(device)

    if 'children' in block_device:
        for p in block_device['children']:
            if p['parttype'] == UUID_SWAP:
                continue
            if p['mountpoint'] is not None:
                log.info("Unmounting partition {}".format(p['mountpoint']))
                unmount(p['mountpoint'])

    if block_device['mountpoint'] is not None:
        log.info("Unmounting {}".format(block_device['mountpoint']))
        unmount(p['mountpoint'])

def efi_enabled() -> bool:
    return os.path.isdir("/sys/firmware/efi/efivars")

def read_partitions_file(wrapper:io.TextIOBase) -> list:

    if not isinstance(wrapper, io.TextIOBase):
        raise TypeError("Wrong type: {}".format(type(wrapper)))

    with wrapper as f:
        data = f.read().strip()

    if data == "":
        raise IOError("No data in partitions file.")

    jsondata = json.loads(data)

    if 'partitions' not in jsondata:
        raise IndexError("No 'partitions' key found in partitions file.")

    partitions = jsondata['partitions']

    if len(partitions) == 0:
        raise IndexError("No partitions in partition file?")

    # Validate keys
    must_have_keys = ["name", "type", "size"]

    for i in partitions:
        for k in must_have_keys:
            if k not in i:
                raise IndexError("key '{}' was not found!".format(k))

    # Convert hex to int
    for i in partitions:
        i['type'] = int(i['type'], 16)

    return partitions

def get_datefmt() -> str:
    return '%H:%M:%S'