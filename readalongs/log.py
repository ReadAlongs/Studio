#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# log.py
#
#   Setup a logger that has colours!
#
#######################################################################

import logging

import coloredlogs

FIELD_STYLES = dict(levelname=dict(color="green", bold=coloredlogs.CAN_USE_BOLD_FONT),)


def setup_logger(name):
    """ Create logger and configure with cool colors!
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(name)

    # Use level='NOTSET' (most permissive) here so whatever level the user later selects
    # does get printed. with level='INFO' here, setting LOGGER.setLevel('DEBUG') in the
    # app doesn't work, and therefore the --debug command line options doesn't work.
    coloredlogs.install(
        level="NOTSET",
        fmt="%(levelname)s - %(message)s",
        logger=logger,
        field_styles=FIELD_STYLES,
    )

    logger.setLevel("INFO")  # default logging level is INFO
    return logger


LOGGER = setup_logger("root")
