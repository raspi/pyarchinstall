#!/bin/env/python

import logging

log = logging.getLogger(__name__)

from funcs import *

__VERSION__ = "0.0.1"
__AUTHOR__ = u"Pekka Järvinen"
__YEAR__ = 2017
__DESCRIPTION__ = u"Arch Installer - Partition generator. Version {0}.".format(__VERSION__)
__EPILOG__ = u"%(prog)s v{0} (c) {1} {2}-".format(__VERSION__, __AUTHOR__, __YEAR__)

__EXAMPLES__ = [
    u'',
    u'-' * 60,
    u'%(prog)s',
    u'-' * 60,
]

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=__DESCRIPTION__,
        epilog=__EPILOG__,
        usage=os.linesep.join(__EXAMPLES__),
    )

    optional = parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')

    optional.add_argument('--verbose', '-v', action='count', required=False, default=0, dest='verbose',
                        help="Be verbose. -vvv.. Be more verbose.")

    optional.add_argument('--partitions <partitions.json>', '-p', type=argparse.FileType('r+', encoding='utf8'), dest='partitionsfile',
                        help='Partitions JSON file. These are created to target device.', default="partitions.json")

    required.add_argument('--device <block device>', '-d', action=FullPaths, type=is_block_device, dest='device',
                        required=True,
                        help='Target device (for example /dev/sda).')

    parser._action_groups.append(optional)

    args = parser.parse_args()

    if int(args.verbose) > 0:
        logging.getLogger().setLevel(logging.DEBUG)
        log.info("Being verbose")

    partitions = read_partitions_file(args.partitionsfile)

    if len(partitions) < 2:
        log.error("There needs to be at least two (2) partitions. (/ and /boot)")
        sys.exit(1)

    unmount_all(args.device)

    block_device = get_block_device(args.device)

    if block_device['group'] == "optical":
        log.error("Block device {} group is optical".format(block_device['name']))
        sys.exit(1)

    if block_device['type'] == "rom":
        log.error("Block device {} type is ROM".format(block_device['name']))
        sys.exit(1)

    bios_partition_exists = False

    for p in partitions:
        if p['type'] == 0xef02:
            bios_partition_exists = True
            break

    if not efi_enabled() and not bios_partition_exists:
        log.error("Your system is not EFI enabled and there's no BIOS partition listed in partition file. Aborting.")
        sys.exit(1)


    if 'children' in block_device:
        keys = ['name', 'fstype', 'mountpoint', 'label', 'partlabel', 'size']
        children = []
        for i in block_device['children']:
            _d = {}
            for k in keys:
                _d[k] = i[k]
            children.append(_d)
        log.info("Block device {} has children. These will be deleted:".format(block_device['name']))
        for i in children:
            log.info("    {}".format(i))

    confirm_delete_disk = input("Delete all contents from {}? y/n: ".format(args.device)).lower()

    if confirm_delete_disk != "y":
        log.info("Aborted.")
        sys.exit(1)

    sgdisk(args.device, ['--zap-all'])
    wipefs(args.device, ['-a'])
    sgdisk(args.device, ["--clear", "--mbrtogpt"])

    log.info("Generating partitions..")
    for idx, partition in enumerate(partitions):
        sgargs = [
            "--new", "0:0:{}".format(partition['size']),
            "--typecode", "0:{:04x}".format(partition['type']),
            "--change-name", "0:{}".format(partition['name']),
        ]
        log.info("Generating partition {} {}".format(partition['name'], "{:04x}".format(partition['type'])))
        sgdisk(args.device, sgargs)

    log.info("Informing OS for partition changes")
    pb_run = partprobe(args.device)
    log.info(pb_run.stdout.decode('utf8'))

    block_device = get_block_device(args.device)

    if 'children' not in block_device:
        log.error("Partition generation failed")
        sys.exit(1)

    log.info("Wiping partitions..")
    for p in block_device['children']:
        dev = "/dev/{}".format(p['name'])
        log.info("  Wiping {}".format(dev))
        sgdisk(dev, ['--zap-all'])
        wipefs(dev, ['-a'])

    log.info("Informing OS for partition changes")
    pb_run = partprobe(args.device)
    log.info(pb_run.stdout.decode('utf8'))

    block_device = get_block_device(args.device)

    log.info("Generating filesystems..")
    for p in block_device['children']:
        dev = "/dev/{}".format(p['name'])
        log.info("  Partition {}".format(dev))
        # log.debug(p)
        if p['parttype'] == UUID_SWAP:
            log.info("  Enabling swap on {}".format(p['name']))
            enable_swap(dev)
        elif p['parttype'] == UUID_BIOS:
            pass
        elif p['parttype'] == UUID_OTHER:
            log.info("  Formatting ext4 @ {}".format(p['name']))
            mkfs_ext4(dev)
        else:
            log.error("  Unknown type: {} {} {}. Format this manually.".format(p['name'], p['partlabel'], p['parttype']))

    log.info("Informing OS for partition changes")
    pb_run = partprobe(args.device)
    log.info(pb_run.stdout.decode('utf8'))

    fdisk_run = fdisk(args.device, ['--list'])
    log.info(fdisk_run.stdout.decode('utf8'))

    log.info("Done.")
