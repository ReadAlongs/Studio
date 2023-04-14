"""This file contains the deprecated readlongs's own get_lang() function until
the latest g2p is published and we can just import that instead"""

# TODO: when g2p is published with https://github.com/roedoejet/g2p/pull/248 merged in,
# remove this file from the repo and change util.get_langs() to just import get_langs
# from g2p without a try/except block.

LANGS = None
LANG_NAMES = None


def get_langs():
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
        # Imports deferred to when the function is actually first called, because
        # they load the g2p database and take a fair bit of time. And importing
        # networkx is also quite expensive.
        import g2p.mappings.langs as g2p_langs
        from networkx import has_path

        # langs_available in g2p lists langs inferred by the directory structure of
        # g2p/mappings/langs, but in ReadAlongs, we need all input languages to any mappings.
        # E.g., for Michif, we need to allow crg-dv and crg-tmd, but not crg, which is what
        # langs_available contains. So we define our own list of languages here.
        langs_available = []

        # this will be the set of all langs in g2p + "eng", which we need temporarily
        full_lang_names = {"eng": "English"}

        for _, v in g2p_langs.LANGS.items():
            for mapping in v["mappings"]:
                # add mapping to names hash table
                full_lang_names[mapping["in_lang"]] = mapping["language_name"]
                # add input id to all available langs list
                if mapping["in_lang"] not in langs_available:
                    langs_available.append(mapping["in_lang"])

        # get the key from all networks in g2p module that have a path to 'eng-arpabet',
        # which is needed for the readalongs
        # Filter out <lang>-ipa: we only want "normal" input languages.
        # Filter out *-norm and crk-no-symbols, these are just intermediate representations.
        LANGS = [
            x
            for x in langs_available
            if not x.endswith("-ipa")
            and not x.endswith("-equiv")
            and not x.endswith("-no-symbols")
            and x not in ["und-ascii", "moh-festival"]
            and g2p_langs.LANGS_NETWORK.has_node(x)
            and has_path(g2p_langs.LANGS_NETWORK, x, "eng-arpabet")
        ]

        # Was required for some older versions of g2p:
        if "eng" not in LANGS:
            LANGS += ["eng"]
        # Sort LANGS so the -h messages list them alphabetically
        LANGS = sorted(LANGS)

        # Set up LANG_NAMES hash table for studio UI to properly name the dropdown options
        LANG_NAMES = {lang_code: full_lang_names[lang_code] for lang_code in LANGS}

        return LANGS, LANG_NAMES
