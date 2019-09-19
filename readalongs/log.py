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

FIELD_STYLES = dict(
    levelname=dict(color='green', bold=coloredlogs.CAN_USE_BOLD_FONT),
)


def setup_logger(name):
    """ Create logger and configure with cool colors!
    """
    logging.basicConfig(
        level=logging.INFO
    )
    logger = logging.getLogger(name)
    coloredlogs.install(level='INFO', fmt='%(levelname)s - %(message)s',
                        logger=logger, field_styles=FIELD_STYLES)
    return logger

LOGGER = setup_logger('root')
