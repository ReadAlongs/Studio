"""
Language support for readalongs.g2p
"""

import os
import glob
import json
import io
from iso639 import languages
from readalongs.lang import __file__ as MAP_DIR_F

MAP_DIR = os.path.dirname(MAP_DIR_F)

def return_lang_name(iso_code: str) -> str:
    ''' Given a three-part iso-639 code, return the name
    '''
    try:
        return languages.get(part3=iso_code).name
    except KeyError:
        return 'Language with 3-part code %s is not declared in ISO-639' % iso_code

def get_langs(mapping_dir=MAP_DIR):
    """Return the names of all languages in lang folder based on their iso-639 codes"""
    langs = []
    for name in os.listdir(MAP_DIR):
        if len(name) == 3:
            langs.append({'code': name, 'name': return_lang_name(name)})
    return sorted(langs, key=lambda x: x['code'])

def base_dir():
    """Get the default directory containing all languages."""
    return os.path.dirname(__file__)


def lang_dir(lang, mapping_dir=None):
    """Get the default resource directory for a language."""
    lang = lang.replace('-', '_')
    lang = lang.replace('_ipa', '')
    if mapping_dir is None:
        mapping_dir = base_dir()
    return os.path.join(mapping_dir, lang)


def lang_dirs(mapping_dir=None):
    """Iterate over the available languages and their resource directories."""
    if mapping_dir is None:
        mapping_dir = base_dir()
    for name in os.listdir(mapping_dir):
        path = lang_dir(name, mapping_dir)
        # Make sure it is a directory with mapping (JSON) files
        if glob.glob(os.path.join(path, '*.json')):
            yield name, path


def get_mapping(src_lang, dst_lang, mapping_dir=None):
    """Get mapping data based on filename conventions."""
    path = os.path.join(lang_dir(src_lang, mapping_dir),
                        '%s_to_%s.json' % (src_lang, dst_lang))
    return json.load(io.open(path))
