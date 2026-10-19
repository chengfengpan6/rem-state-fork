"""Deterministic DGP and researcher-only quantities. Never send REL to actors."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from itertools import combinations
from math import comb
import random
from typing import Mapping

CONTEXTS = ("X", "Y", "Z")
SOURCES = ("A", "B", "C")
REL = {"X": {"A": .85, "B": .65, "C": .50},
       "Y": {"A": .50, "B": .85, "C": .65},
       "Z": {"A": .65, "B": .50, "C": .85}}
TRUTH_DESIGN = "iid_bernoulli_0.5"
DGP_VERSION = "context3-iidtruth-v1"


@dataclass(frozen=True)
class Event:
    round_index: int
    context: str
    truth: int
    signals: tuple[int, int, int]

    def signal_dict(self):
        return dict(zip(SOURCES, self.signals))

    def observed_record(self):
        return {"round_index": self.round_index, "context": self.context,
                "signals": self.signal_dict(), "truth": self.truth}


def generate_tape(seed: int, formation_rounds: int, post_rounds: int) -> tuple[Event, ...]:
    """Balance contexts within 3 rounds, but draw each truth independently.

    This deliberately differs from the manuscript's exact truth quotas. No quota
    can reveal a later truth, and the oracle prior conditional on past is .5.
    All signals are conditionally independent given context and truth.
    """
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 or x % 3
           for x in (formation_rounds, post_rounds)):
        raise ValueError("Both horizons must be positive multiples of 3")
    rng = random.Random(seed)
    events = []
    for start in range(0, formation_rounds + post_rounds, 3):
        order = list(CONTEXTS)
        rng.shuffle(order)
        for offset, context in enumerate(order):
            truth = rng.randrange(2)
            signals = tuple(truth if rng.random() < REL[context][source] else 1-truth
                            for source in SOURCES)
            events.append(Event(start+offset+1, context, truth, signals))
    return tuple(events)


def oracle_probability(context: str, signals: Mapping[str, int], prior=.5) -> float:
    """Exact Bayes posterior under the implemented IID-truth DGP.

    Accepts a subset of source signals, but final performance uses all three.
    The known reliability matrix is researcher-only and never actor input.
    """
    if context not in CONTEXTS or not 0 <= prior <= 1:
        raise ValueError("Invalid context or prior")
    likelihood_one, likelihood_zero = prior, 1-prior
    for source, signal in signals.items():
        if source not in SOURCES or signal not in (0, 1):
            raise ValueError("Invalid labeled signal")
        reliability = REL[context][source]
        likelihood_one *= reliability if signal else 1-reliability
        likelihood_zero *= 1-reliability if signal else reliability
    denominator = likelihood_one + likelihood_zero
    if not denominator:
        raise ValueError("Impossible evidence")
    return likelihood_one / denominator


def ledger_counts(ledger: list[dict]) -> dict:
    counts = {c: {s: {"correct": 0, "n": 0} for s in SOURCES} for c in CONTEXTS}
    for row in ledger:
        for source, signal in row["signals"].items():
            cell = counts[row["context"]][source]
            cell["n"] += 1
            cell["correct"] += int(signal == row["truth"])
    return counts


def evidence_map(ledger: list[dict]) -> dict:
    """Beta(1,1) posterior mean and equal-tail 90% credible interval.

    E's mathematical credible intervals and actors' subjective intervals share
    the output schema; they are not claimed to be psychologically equivalent.
    """
    from scipy.stats import beta
    counts = ledger_counts(ledger)
    cells = []
    for c in CONTEXTS:
        for s in SOURCES:
            v = counts[c][s]
            a, b = 1+v["correct"], 1+v["n"]-v["correct"]
            cells.append({"context": c, "source": s, "estimate": a/(a+b),
                          "lower": float(beta.ppf(.05, a, b)), "upper": float(beta.ppf(.95, a, b))})
    return {"cells": cells}


def pair_probability_exact(correct_a: int, correct_b: int, n: int) -> Fraction:
    """P(Beta(1+a,1+n-a)>Beta(1+b,1+n-b)), exactly as a rational.

    Both sources have equal observation count within the context. In particular
    equal correct counts give exactly 1/2, avoiding the original tie bug.
    """
    if not 0 <= correct_a <= n or not 0 <= correct_b <= n:
        raise ValueError("Counts must lie between 0 and n")
    m, k = n+1, correct_a+correct_b+1
    numerator = sum(comb(m, y)*comb(m, k-y)
                    for y in range(max(correct_b+1, k-m), min(k, m)+1))
    return Fraction(numerator, comb(2*m, k))


def history_metrics(ledger: list[dict]) -> dict:
    counts = ledger_counts(ledger)
    signed = []
    pairs = []
    for context in CONTEXTS:
        for a, b in combinations(SOURCES, 2):
            ca, cb = counts[context][a], counts[context][b]
            if ca["n"] != cb["n"]:
                raise ValueError("Pair comparison requires equal observation counts")
            probability = pair_probability_exact(ca["correct"], cb["correct"], ca["n"])
            sign = 1 if REL[context][a] > REL[context][b] else -1
            concordance = sign*(2*probability-1)
            signed.append(concordance)
            pairs.append({"context": context, "source_a": a, "source_b": b,
                          "true_order_probability": float(probability if sign > 0 else 1-probability),
                          "strict_reversal": concordance < 0,
                          "signed_concordance": float(concordance)})
    m = -sum(signed, Fraction(0, 1))/len(signed)
    return {"M": float(m), "M_exact": {"numerator": m.numerator, "denominator": m.denominator},
            "strict_reversal_count": sum(x["strict_reversal"] for x in pairs),
            "worst_pair_concordance": float(min(signed)), "pairs": pairs}


def brier(probability, truth):
    return (probability-truth)**2


def conditional_brier_regret(probability, oracle):
    return (probability-oracle)**2

