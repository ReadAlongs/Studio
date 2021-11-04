import g2p.mappings.langs as g2p_langs
from networkx import has_path

LANGS = None
LANG_NAMES = None


def getLangs():
    """Get the list of language codes and names supported by the g2p library

    Returns:
        LANGS (List[str]), LANG_NAMES (Dict[str,str]):
            LANGS is the list of valid language codes supported
            LANG_NAMES maps each code to its full language name
    """

    global LANGS
    global LANG_NAMES

    if LANGS is not None and LANG_NAMES is not None:
        # Cache the results so we only calculate this information once.
        return LANGS, LANG_NAMES
    else:
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
        return LANGS, LANG_NAMES
