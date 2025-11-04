#!/usr/bin/env python

"""
Accuracy, Precision, Recall, F1 calculations for our g2p and RAS papers.

Author: Eric Joanis
Copyright (c) 2022, National Research Council Canada
LICENSE: MIT

Requirements: pip install pympi-ling click
Tested with:
 - pympi-ling==1.69 click==8.0.4 but expected to work with more recent
 - Python from 3.7 to 3.11

Typical usage: python accuracy.py gold.TextGrid candidate.TextGrid

run "python accuracy.py --help" for more usage details.
"""

import statistics
import sys
import unicodedata as ud
from typing import List, Tuple

import click
from pympi.Praat import TextGrid


def keep_word(word):
    """Return whether to keep the given word or treat it as a silence"""
    word = word.strip()
    return word != "" and word != "<unk-removed>"


def get_words(textgrid_file: str) -> List[Tuple[float, float, str]]:
    """Open a TextGrid file, and return a list of the words, from the word tier

    Returns: List[Tuple[start: float, end: float, word_text: str]]
    """
    textgrid_data = None
    for codec in "utf-8", "utf-16", "utf-16-be", "utf-16-le":
        try:
            textgrid_data = TextGrid(textgrid_file, codec=codec)
            break
        except Exception:
            pass
    if textgrid_data is None:
        raise click.BadParameter(f"File {textgrid_file} does not appear to be valid")

    word_tier = None
    for tier_name in "Word", "words":
        try:
            word_tier = textgrid_data.get_tier(tier_name)
        except IndexError:
            pass
    if word_tier is None:
        raise click.BadParameter(f"Did not find a word(s) layers in {textgrid_file}")

    return [
        interval for interval in word_tier.get_intervals() if keep_word(interval[2])
    ]


def normalize(word):
    """Normalize the spelling of words to help match between GOLD and CANDIDATE"""
    word = word.strip()
    word = ud.normalize("NFC", word)
    word = word.lower()
    word = word.replace("’", "'")
    word = word.replace(",", "")
    return word


def calc_recall(gold_word, cand_word):
    """Recall is defined as how much of gold_word is within the span of cand_word

    Returns: (recall, numerator, denominator)
    """
    gold_start, gold_end, _ = gold_word
    cand_start, cand_end, _ = cand_word
    gold_len = gold_end - gold_start
    overlap_len = max(0, min(gold_end, cand_end) - max(gold_start, cand_start))
    return overlap_len / gold_len, overlap_len, gold_len


def calc_precision(gold_word, cand_word, prev_gold_word, next_gold_word):
    """Precision is defined as what proportion of cand_word is inside
    gold_word, ignoring part of cand_word that are silences just before or
    after gold_word

    Returns: (precision, numerator, denominator)
    """
    gold_start, gold_end, _ = gold_word
    cand_start, cand_end, _ = cand_word
    prev_gold_end = prev_gold_word[1] if prev_gold_word else 0
    next_gold_start = next_gold_word[0] if next_gold_word else max(gold_end, cand_end)

    left_error = max(0, prev_gold_end - cand_start)
    right_error = max(0, cand_end - next_gold_start)
    overlap_len = max(0, min(gold_end, cand_end) - max(gold_start, cand_start))

    denominator = left_error + overlap_len + right_error
    precision = overlap_len / denominator if overlap_len else 0
    return precision, overlap_len, denominator


def calc_f1(precision, recall):
    """F1 following the formula at https://en.wikipedia.org/wiki/F-score"""

    return 2 * precision * recall / (precision + recall)


def histogram(values):
    """Return a 6-tuple: <=0, <=.25, <=.50, <=.75, <1, >=1"""
    hist = [0] * 6
    for value in values:
        if value <= 0:
            hist[0] += 1
        elif value <= 0.25:
            hist[1] += 1
        elif value <= 0.50:
            hist[2] += 1
        elif value <= 0.75:
            hist[3] += 1
        elif value < 1.0:
            hist[4] += 1
        else:
            hist[5] += 1
    return hist


def describe_values(values, title):
    """Prints a number of informative statistics on screen and returns the average"""
    print(f"Distribution of {title} values:")
    hist = histogram(values)
    count = len(values)
    print(
        "histogram (<=0, <=.25, <=.50, <=.75, <1, ==1):",
        ", ".join(str(n) for n in hist),
    )
    print("histogram in fractions:", ", ".join([f"{n / count:.4f}" for n in hist]))
    average = sum(values) / count
    print(f"sum: {sum(values):.2f} count: {count} avg: {average:.4f}")
    print()
    return average


def display_gold_stats(gold_words):
    """Display average, median, max, min for the gold word lengths"""
    print("Distribution of gold word durations")
    gold_lengths = [end - start for start, end, _ in gold_words]
    for measure in min, max, statistics.mean, statistics.median:
        print(f"{measure.__name__}: {measure(gold_lengths)}")
    print()


def shift_times(words, shift_ms):
    """Shift all the times in words by adding shift_ms ms to them."""
    shift_s = shift_ms / 1000
    for i, (start, end, word) in enumerate(words):
        words[i] = (start + shift_s, end + shift_s, word)


@click.command()
@click.option("-d", "--debug", help="Spew debugging info", is_flag=True)
@click.option(
    "-t",
    "--thresholds",
    default="10,25,50,100",
    help="comma-separated list of thresholds in ms [10,25,50,100]",
)
@click.option("--gold-stats", is_flag=True, help="Show descriptive statistics for GOLD")
@click.option(
    "--shift-ms", type=float, default=0.0, help="Shift all CANDIDATE times by FLOAT ms"
)
@click.argument("gold", type=click.Path(exists=True, dir_okay=False))
@click.argument(
    "candidate", type=click.Path(exists=True, dir_okay=False), required=False
)
def main(
    gold: str,
    candidate: str,
    gold_stats: bool,
    thresholds: str,
    debug: bool,
    shift_ms: float,
):
    """Calculate the accuracy of CANDIDATE alignments against the GOLD standard."""
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

    threshold_list = thresholds.split(",")
    threshold_seconds = [int(t) / 1000 for t in threshold_list]

    gold_words = get_words(gold)
    if gold_stats:
        display_gold_stats(gold_words)

    if not candidate:
        if not gold_stats:
            raise click.BadParameter(
                "Nothing to do, provide one of CANDIDATE or --gold-stats"
            )
        return

    candidate_words = get_words(candidate)
    if shift_ms != 0.0:
        shift_times(candidate_words, shift_ms)

    word_mismatch_count = 0
    matches = [0] * len(threshold_list)

    def add_matches(gold_pos, cand_pos):
        for i, t in enumerate(threshold_seconds):
            if abs(cand_pos - gold_pos) < t:
                matches[i] += 1

    recall_list = []  # for averaged R, F1
    recall_num_total, recall_denom_total = 0, 0  # for accumulated R, F1
    precision_list = []  # for averaged R,P,F1
    precision_num_total, precision_denom_total = 0, 0  # for accumulated P, F1

    ext_gold = [None, *gold_words, None]
    for prev_g, g, next_g, c in zip(
        ext_gold, gold_words, ext_gold[2:], candidate_words
    ):
        if normalize(g[2]) != normalize(c[2]):
            word_mismatch_count += 1
            print(g, c, " ----  MISMATCHED WORD")
        else:
            if debug:
                print(g, c)
        add_matches(g[0], c[0])
        add_matches(g[1], c[1])
        recall, numerator, denom = calc_recall(g, c)
        recall_list.append(recall)
        recall_num_total += numerator
        recall_denom_total += denom
        precision, numerator, denom = calc_precision(g, c, prev_g, next_g)
        precision_list.append(precision)
        precision_num_total += numerator
        precision_denom_total += denom
        # print(g, c, f"r={recall:.4f} p={precision:.4f}")

    delta_words = len(gold_words) - len(candidate_words)
    if delta_words > 0:
        for g in gold_words[len(candidate_words) :]:
            print(g, " ----  EXTRA GOLD WORD")
        print(f"Gold has {delta_words} more word(s) than Candidate.")
    if delta_words < 0:
        for c in candidate_words[len(gold_words) :]:
            print("\t\t\t\t", c, " ----  EXTRA CANDIDATE WORD")
        print(f"Candidate has {-delta_words} more word(s) than Gold.")
    print("Word count:", len(gold_words))
    print("Word mismatches:", word_mismatch_count)

    # Accuracy calculations for word boundaries
    denominator = 2 * len(gold_words)
    scores = [num / denominator for num in matches]
    print(" &\t".join(f"<{t}" for t in threshold_list))
    print(" &\t".join(f"{score:.2f}" for score in scores))
    print()

    # P/R/F1 distributions for whole words
    avg_precision = describe_values(precision_list, "Precision")
    avg_recall = describe_values(recall_list, "Recall")

    # Averaged P/R/F1 for whole words
    print(
        f"Average p={avg_precision:.4f} r={avg_recall:.4f} F1={calc_f1(avg_precision, avg_recall):.4f}"
    )

    # Accumulated P/R/F1 for whole words
    acc_precision = precision_num_total / precision_denom_total
    acc_recall = recall_num_total / recall_denom_total
    print(
        f"Accumulated p={acc_precision:.4f} r={acc_recall:.4f} F1={calc_f1(acc_precision, acc_recall):.4f}"
    )
    print()


if __name__ == "__main__":
    main()
