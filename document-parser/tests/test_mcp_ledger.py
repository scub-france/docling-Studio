"""Tests for the MCP usage tally.

The tally exists to answer a question a single result cannot: what has this
surface cost so far. So the tests are about accumulation, isolation between
servers, and what is deliberately left out of the measurement.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.navigation import estimate_tokens
from mcp_adapter.ledger import Ledger


@dataclass(frozen=True)
class _Payload:
    text: str
    page_image: str | None = None


class TestLedger:
    def test_starts_empty(self):
        usage = Ledger().snapshot()
        assert usage == type(usage)(calls=0, est_tokens=0)

    def test_records_what_the_client_will_read(self):
        ledger = Ledger()
        payload = _Payload(text="hello")
        ledger.record(payload)
        usage = ledger.snapshot()
        assert usage.calls == 1
        # The whole JSON, envelope included — that is what lands in a context,
        # not the bare field values.
        assert usage.est_tokens == estimate_tokens('{"text": "hello"}')

    def test_hands_the_payload_straight_back(self):
        # So a tool stays a mapping: `return ledger.record(outline_result(...))`.
        ledger = Ledger()
        payload = _Payload(text="x")
        assert ledger.record(payload) is payload

    def test_accumulates_across_calls(self):
        ledger = Ledger()
        for _ in range(3):
            ledger.record(_Payload(text="hello"))
        usage = ledger.snapshot()
        assert usage.calls == 3
        assert usage.est_tokens == 3 * estimate_tokens('{"text": "hello"}')

    def test_the_page_raster_is_not_priced_in_tokens(self):
        # An image is not text; pricing it per-4-characters would be a figure
        # with no meaning attached to it.
        plain = Ledger()
        plain.record(_Payload(text="hello"))
        with_image = Ledger()
        with_image.record(_Payload(text="hello", page_image="data:image/png;base64," + "A" * 5000))
        assert with_image.snapshot().est_tokens == plain.snapshot().est_tokens

    def test_two_servers_do_not_pool_their_totals(self):
        # The reason this is an instance and not a module-level global: a test
        # suite builds dozens of servers, and a leaked tally would make every
        # assertion depend on test order.
        first, second = Ledger(), Ledger()
        first.record(_Payload(text="hello"))
        assert second.snapshot().calls == 0

    def test_an_unserialisable_value_costs_a_measurement_not_a_failure(self):
        # A tally is never worth failing a tool call over.
        ledger = Ledger()
        ledger.record(_Payload(text=object()))  # type: ignore[arg-type]
        assert ledger.snapshot().calls == 1
