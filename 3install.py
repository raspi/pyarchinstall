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

    optional.add_argument('--partitions <partitions.json>', '-p', type=argparse.FileType('r+', encoding='utf8'),
                          dest='partitionsfile',
                          help='Partitions JSON file.', default="partitions.json")

    required.add_argument('--device <block device>', '-d', action=FullPaths, type=is_block_device, dest='device',
                          required=True,
                          help='Target device (for example /dev/sda).')

    parser._action_groups.append(optional)

    args = parser.parse_args()

    if int(args.verbose) > 0:
        logging.getLogger().setLevel(logging.DEBUG)
        log.info("Being verbose")

    block_device = get_block_device(args.device)

    if 'children' not in block_device:
        log.error("No partitions found??")
        sys.exit(1)

    must_find = ["/", "/boot"]
    found = []

    for p in block_device['children']:
        if p['parttype'] == UUID_SWAP:
            continue
        if p['parttype'] == UUID_BIOS:
            continue

        if p['mountpoint'] is not None:
            found.append(p['mountpoint'])

    if not os.path.isdir(INSTALL_DIR_PREFIX):
        log.error("Not a dir: {}".format(INSTALL_DIR_PREFIX))
        sys.exit(1)

    # pacman mirror files in boot ISO
    pacman_mirror_file = os.path.join("/etc", "pacman.d", "mirrorlist")
    pacman_mirror_file_orig = os.path.join(pacman_mirror_file, ".orig")
    pacman_mirror_file_backup = os.path.join(pacman_mirror_file, ".backup")

    # copy original file
    if not os.path.isfile(pacman_mirror_file_orig):
        shutil.copy(pacman_mirror_file, pacman_mirror_file_orig)

    with open(pacman_mirror_file_backup, 'w+', encoding="utf8") as backup:
        # Read servers off from mirror original file
        with open(pacman_mirror_file_orig, 'r', encoding="utf8") as f:
            for line in f:
                add = False
                line = line.strip()

                if line == "":
                    continue

                if line.lower().find("#Server".lower()) != -1:
                    line = line.lstrip("#")
                    add = True
                if line[0] != "#":
                    add = True

                if add:
                    log.debug("Adding: {}".format(line))
                    backup.write("{}\n".format(line))

    #with open(pacman_mirror_file_backup, 'r', encoding="utf8") as f:
    #    log.info("{}:".format(f.name))
    #    for line in f:
    #        line = line.strip()
    #        print(line)

    log.info("Ranking mirrors.. Please wait..")
    rankings = []
    rank = rankmirrors(pacman_mirror_file_backup)
    for line in rank.stdout.decode('utf8').split("\n"):
        line = line.strip()
        if line.find("#") == 0:
            continue

        if line.lower().find("Server".lower()) != -1:
            rankings.append(line)

    # add ranked mirrors to file
    with open(pacman_mirror_file, 'w', encoding="utf8") as f:
        for r in rankings:
            f.write("{}\n".format(r))


    pacstrap(INSTALL_DIR_PREFIX, ['base'])

    with open(os.path.join(INSTALL_DIR_PREFIX, "etc", "fstab")) as f:
        fstab = genfstab(INSTALL_DIR_PREFIX)
        for line in fstab.stdout.decode('utf8').split("\n"):
            f.write("{}\n".format(line))


    chroot(INSTALL_DIR_PREFIX)