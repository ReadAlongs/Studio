###################################################
#
# add_elements_to_xml.py
#
# In order to streamline the image-adding process, this module
# allows graphics for pages to be specified in a supplementary json
# configuration file.
#
# It also include a more general-purpose XML markup mechanism in add_supplementary_xml
#
# See test.images for more information
#
###################################################

from lxml import etree

from readalongs.log import LOGGER


def add_images(element: etree, config: dict) -> etree:
    """Add images from configuration object to xml

    Args:
        element (etree): xml without images
        config (dict): standard ReadAlong-Studio configuration

    Returns:
        etree: xml with images markup
    """
    if "images" not in config:
        raise KeyError(
            "Configuration tried to add images, but no images were found in configuration"
        )

    if not isinstance(config["images"], dict):
        raise TypeError(
            f"Image configuration is of type {type(config['images'])} but a dict is required."
        )

    pages = element.xpath('//div[@type="page"]')

    for i, url in config["images"].items():
        image_el = etree.Element("graphic", url=url)
        try:
            i = int(i)
        except ValueError as e:
            raise ValueError(
                f"Images must be indexed using integers, you provided {i}"
            ) from e
        try:
            pages[int(i)].append(image_el)
        except IndexError as e:
            raise IndexError(
                f"No page found at index {i}, please verify your configuration"
            ) from e

    return element


def add_supplementary_xml(element: etree, config: dict) -> etree:
    """Add arbitrary xml from configuration object to xml

    Args:
        element (etree): original xml document
        config (dict): standard ReadAlong-Studio configuration

    Returns:
        etree: xml with supplemental markup
    """
    if "xml" not in config:
        raise KeyError(
            "Configuration tried to add supplementary xml, but no declarations "
            "were found in configuration"
        )
    for el in config["xml"]:
        parents = element.xpath(el["xpath"])
        if not parents:
            LOGGER.warning(
                f"No elements found at {el['xpath']}, please verify your configuration."
            )
        for parent in parents:
            parent.append(etree.XML(el["value"]))

    return element
