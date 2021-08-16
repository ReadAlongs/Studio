import g2p.mappings.langs as g2p_langs
from networkx import has_path


def getLangs():
    # LANGS_AVAILABLE in g2p lists langs inferred by the directory structure of
    # g2p/mappings/langs, but in ReadAlongs, we need all input languages to any mappings.
    # E.g., for Michif, we need to allow crg-dv and crg-tmd, but not crg, which is what
    # LANGS_AVAILABLE contains. So we define our own list of languages here.
    LANGS_AVAILABLE = []

    # Set up LANG_NAMES hash table for studio UI to
    # properly name the dropdown options
    LANG_NAMES = {"eng": "English"}

    for k, v in g2p_langs.LANGS.items():
        for mapping in v["mappings"]:
            # add mapping to names hash table
            LANG_NAMES[mapping["in_lang"]] = mapping["language_name"]
            # add input id to all available langs list
            if mapping["in_lang"] not in LANGS_AVAILABLE:
                LANGS_AVAILABLE.append(mapping["in_lang"])

    # get the key from all networks in g2p module that have a path to 'eng-arpabet',
    # which is needed for the readalongs
    # Filter out <lang>-ipa: we only want "normal" input languages.
    # Filter out *-norm and crk-no-symbols, these are just intermediate representations.
    LANGS = [
        x
        for x in LANGS_AVAILABLE
        if not x.endswith("-ipa")
        and not x.endswith("-equiv")
        and not x.endswith("-no-symbols")
        and g2p_langs.LANGS_NETWORK.has_node(x)
        and has_path(g2p_langs.LANGS_NETWORK, x, "eng-arpabet")
    ]

    # Hack to allow old English LexiconG2P
    LANGS += ["eng"]
    # Sort LANGS so the -h messages list them alphabetically
    LANGS = sorted(LANGS)
    return LANGS


def parse_g2p_fallback(g2p_fallback_arg):
    """Parse the strings containing a colon-separated list of fallback args into a
    Python list of language codes, or empty if None
    """
    if g2p_fallback_arg:
        g2p_fallbacks = g2p_fallback_arg.split(":")
        for lang in g2p_fallbacks:
            if lang not in LANGS:
                raise click.BadParameter(
                    f'g2p fallback lang "{lang}" is not valid; choose among {", ".join(LANGS)}'
                )
        return g2p_fallbacks
    else:
        return []
