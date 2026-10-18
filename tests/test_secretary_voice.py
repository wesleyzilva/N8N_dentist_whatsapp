import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.domains.secretary.voice import render_reply


def test_availability_without_slots_asks_and_does_not_invent_time():
    reply = render_reply(
        "AVAILABILITY",
        claims={
            "allowed": [],
            "blocked": ["availability_slots"],
            "can_assert_facts": False,
        },
        evidence={},
    )
    assert "agenda" in reply.lower()
    assert "14" not in reply
    assert "amanhã" not in reply.lower()
    assert "horario invent" not in reply.lower()


def test_location_without_presence_does_not_name_doctor_city():
    reply = render_reply(
        "LOCATION",
        claims={
            "allowed": [],
            "blocked": ["doctor_presence_city"],
            "can_assert_facts": False,
        },
    )
    lowered = reply.lower()
    assert "pato branco" not in lowered
    assert "são carlos" not in lowered
    assert "sao carlos" not in lowered


def test_confirm_uses_human_template():
    reply = render_reply(
        "CONFIRM",
        claims={"allowed": [], "blocked": [], "can_assert_facts": True},
    )
    lowered = reply.lower()
    assert "confirmação" in lowered or "atendimento" in lowered
    assert "dentista" not in lowered


def test_slots_only_when_allowed():
    reply = render_reply(
        "AVAILABILITY",
        claims={
            "allowed": ["availability_slots"],
            "blocked": [],
            "can_assert_facts": True,
        },
        evidence={"availability_slots": [{"start": "2026-10-17T14:00:00-03:00"}]},
    )
    assert "2026-10-17T14:00:00-03:00" in reply


def test_unknown_names_hof_not_general_dentistry():
    reply = render_reply(
        "UNKNOWN",
        claims={"allowed": [], "blocked": [], "can_assert_facts": True},
    )
    lowered = reply.lower()
    assert "harmonização orofacial" in lowered
    assert "odontológic" not in lowered
    assert "dentista" not in lowered
