"""Grounding integrity: no claim ships without a real backing query.

This is how KALMAN proves it never hallucinated a number — the same
"the data proves it, the AI only explains it" discipline as the detector.
"""
from kalman.agents.scribe import Claim, Postmortem, grounded


def test_grounded_when_every_claim_cites_a_real_query():
    pm = Postmortem(
        "inc-1",
        "eu-west edge failure",
        [Claim("cdn_5xx_rate hit 62/s in eu-west", "q1"), Claim("rebuffer_ratio rose to 0.09", "q2")],
    )
    assert grounded(pm, {"q1", "q2", "q3"}) is True


def test_not_grounded_when_a_claim_has_no_query():
    pm = Postmortem("inc-1", "s", [Claim("a number nobody measured", "q9")])
    assert grounded(pm, {"q1", "q2"}) is False
