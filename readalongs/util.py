import re
from collections.abc import Iterable

import click


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
    # Defer expensive import, which loads the whole g2p database
    from g2p import get_arpabet_langs

    return get_arpabet_langs()


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
