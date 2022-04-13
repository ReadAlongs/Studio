import re
from collections.abc import Iterable
from itertools import tee

import click

LANGS = None
LANG_NAMES = None


def get_langs_deferred() -> Iterable:
    """Lazilly get the list of language codes supported by g2p library

    Yields an Iterable in such a way that the g2p database is only loaded when
    the results are iterated over, rather than when this function is called.
    """
    yield from get_langs()[0]


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


# For backwards compatibility, we keep the old names getLangs and getLangsDeferred around.
# For example, ReadAlongsDesktop
# (https://github.com/tobyatgithub/ReadalongsDesktop) depended on the old name,
# and even when it's updated, it'll be helpful to avoid breaking older versions.
getLangs = get_langs
getLangsDeferred = get_langs_deferred


class JoinerCallbackForClick:
    """Command-line parameter validation for multiple-value options.

    The values can be repeated by giving the option multiple times on the
    command line, or by joining them with strings matching joiner_re (colon or
    comma, arbitrarily mixed, by default).

    Matching is case insensitive iff drop_case is True.
    """

    def __init__(self, valid_values: Iterable, joiner_re=r"[,:]", drop_case=False):
        """Get a joiner callback.

        Args:
            valid_values: list of valid values for the multi-value option
            joiner_re: regex for how to user may join multiple values
            drop_case: when true, processed results will be converted to lowercase
        """
        self.valid_values = valid_values  # ***do not convert this to a list here!***
        self.joiner_re = joiner_re
        self.drop_case = drop_case

    # This signature meets the requirements of click.option's callback parameter:
    def __call__(self, _ctx=None, _param=None, value_groups=()):
        # Potentially expensive expansion actually required here, so do it now.
        self.valid_values = list(self.valid_values)
        if self.drop_case:
            self.valid_values = [value.lower() for value in self.valid_values]
        results = [
            value.strip()
            for value_group in value_groups
            for value in re.split(self.joiner_re, value_group)
        ]
        if self.drop_case:
            results = [value.lower() for value in results]
        for value in results:
            if value not in self.valid_values:
                raise click.BadParameter(
                    f"'{value}' is not one of {self.quoted_list(self.valid_values)}."
                )
        return results

    @staticmethod
    def quoted_list(values):
        """Display a list of values quoted, for easy reading in error messages."""
        return ", ".join("'" + v + "'" for v in values)


def get_obsolete_callback_for_click(message):
    """Click callback for telling the user an option is obsolete in a helpful way.

    Args:
        message (str): message telling the user what the option is replaced by
    """

    def _callback(_ctx, param, value_groups):
        if value_groups:
            joiner = "' / '"
            raise click.BadParameter(
                f"The '{joiner.join(param.opts)}' option is obsolete.\n" + message
            )

    return _callback
