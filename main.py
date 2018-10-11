#!/bin/env/python

import logging

log = logging.getLogger(__name__)

from funcs import *

__VERSION__ = "0.0.1"
__AUTHOR__ = u"Pekka Järvinen"
__YEAR__ = 2017
__DESCRIPTION__ = u"Arch Installer. Version {0}.".format(__VERSION__)
__EPILOG__ = u"%(prog)s v{0} (c) {1} {2}-".format(__VERSION__, __AUTHOR__, __YEAR__)

__EXAMPLES__ = [
    u'',
    u'-' * 60,
    u'%(prog)s',
    u'-' * 60,
]

UUID_SWAP = "0657fd6d-a4ab-43c4-84e5-0933c84b4f4f"

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

    optional.add_argument('--config <file.ini>', '-c', type=argparse.FileType('r+', encoding='utf8'), dest='file',
                        help='Config file.', default="install.ini")

    optional.add_argument('--partitions <partitions>', '-p', type=argparse.FileType('r+', encoding='utf8'), dest='partitionsfile',
                        help='Partitions JSON file.', default="partitions.json")

    required.add_argument('--device <block device>', '-d', action=FullPaths, type=is_block_device, dest='device',
                        required=True,
                        help='Target device (for example /dev/sda).')

    parser._action_groups.append(optional)

    args = parser.parse_args()

    if int(args.verbose) > 0:
        logging.getLogger().setLevel(logging.DEBUG)
        log.info("Being verbose")

    ntp_is_in_sync = False

    run_timedatectl_status = ["timedatectl", "status"]
    log.info("Running {}".format(run_timedatectl_status))

    timedatectl_status = subprocess.run(run_timedatectl_status, timeout=10, shell=True, check=True, stdout=subprocess.PIPE)

    for i in timedatectl_status.stdout.decode('utf8').split("\n"):
        i = i.strip()
        if i.lower() == "System clock synchronized: yes".lower():
            ntp_is_in_sync = True

    if not ntp_is_in_sync:
        run = ["timedatectl", "set-ntp", "true"]
        log.debug("Running {}".format(" ".join(run)))
        timedatectl_run = subprocess.run(run, timeout=10, check=True, stdout=subprocess.PIPE)

    while not ntp_is_in_sync:
        log.info("Running {}".format(run_timedatectl_status))
        timedatectl_status = subprocess.run(run_timedatectl_status, timeout=10, shell=True, check=True, stdout=subprocess.PIPE)

        for i in timedatectl_status.stdout.decode('utf8').split("\n"):
            i = i.strip()

            if i.lower() == "System clock synchronized: yes".lower():
                ntp_is_in_sync = True

        if not ntp_is_in_sync:
            log.info("Waiting clock sync..")
            time.sleep(1)


    log.info("Done.")
