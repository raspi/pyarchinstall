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

    required.add_argument('--device <block device>', '-d', action=FullPaths, type=is_block_device, dest='device',
                        required=True,
                        help='Target device (for example /dev/sda).')

    parser._action_groups.append(optional)

    args = parser.parse_args()

    if int(args.verbose) > 0:
        logging.getLogger().setLevel(logging.DEBUG)
        log.info("Being verbose")

    unmount_all(args.device)

    block_device = get_block_device(args.device)

    if 'children' not in block_device:
        log.error("No partitions found??")
        sys.exit(1)

    os.makedirs(os.path.join(INSTALL_DIR_PREFIX), exist_ok=True)

    if not os.path.isdir(INSTALL_DIR_PREFIX):
        log.error("Not a dir: {}".format(INSTALL_DIR_PREFIX))
        sys.exit(1)

    log.info("Mounting partitions..")

    # mount last partition as /
    # must exist before /boot
    for p in reversed(block_device['children']):
        dev = "/dev/{}".format(p['name'])

        if p['parttype'] == UUID_SWAP:
            continue
        elif p['parttype'] == UUID_BIOS:
            continue
        elif p['parttype'] == UUID_OTHER:
            mount(dev, INSTALL_DIR_PREFIX)
            break

    # Mount first as "/boot"
    for p in block_device['children']:
        dev = "/dev/{}".format(p['name'])

        if p['parttype'] == UUID_SWAP:
            continue
        elif p['parttype'] == UUID_BIOS:
            continue
        elif p['parttype'] == UUID_OTHER:
            BOOTDIR = os.path.join(INSTALL_DIR_PREFIX, "boot")
            os.makedirs(BOOTDIR, exist_ok=True)
            mount(dev, BOOTDIR)
            break

    for p in get_block_device(args.device)['children']:
        print(p['mountpoint'])
