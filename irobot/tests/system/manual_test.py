import logging

from irobot.tests.system._common import StandaloneIrods, StandaloneAuthenticationServer, StandaloneIrobot

ESCAPE_INPUT = "q"
REBUILD_INPUT = "r"

logger = logging.root
logger.setLevel(logging.INFO)


def main():
    irods = StandaloneIrods()
    authentication_server = StandaloneAuthenticationServer()
    irobot = StandaloneIrobot(authentication_server, irods)
    input_keys = None

    logging.info("Building iRobot...")
    StandaloneIrobot.build_irobot()
    logging.info("Starting iRobot...")

    try:
        while input_keys != ESCAPE_INPUT:
            print(f"iRobot running at: {irobot.url}")
            input_keys = input(f"Input \"{ESCAPE_INPUT}\" to stop or \"{REBUILD_INPUT}\" to rebuild and restart the "
                               f"iRobot server")
            if input_keys == REBUILD_INPUT:
                logger.info("Stopping iRobot...")
                irobot.tear_down()
                logging.info("Rebuilding iRobot...")
                StandaloneIrobot.irobot_built = False
                StandaloneIrobot.build_irobot()
                logging.info("Starting iRobot...")
    finally:
        logger.info("Stopping iRODS...")
        irods.tear_down()
        logger.info("Stopping authentication server...")
        authentication_server.tear_down()
        logger.info("Stopping iRobot...")
        irobot.tear_down()

    logger.info("Stopped!")


if __name__ == "__main__":
    main()
