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

    parser._action_groups.append(optional)

    args = parser.parse_args()

    if int(args.verbose) > 0:
        logging.getLogger().setLevel(logging.DEBUG)
        log.info("Being verbose")

    adapters = []
    for dev in pathlib.Path("/sys/class/net/").resolve().iterdir():
        dev = pathlib.Path(dev).resolve()
        if os.path.basename(dev) == "lo":
            continue

        adapters.append(str(dev))

    if len(adapters) == 0:
        log.error("No network adapters found.")
        sys.exit(1)

    print (adapters)
