from types import SimpleNamespace

from PhyAgentOS.agent.experience.evolution_composition import compose_evolution_extension


class _Store:
    def __init__(self):
        self.events = []

    def record_event(self, event_type, ref, payload=None):
        self.events.append((event_type, ref, payload))


class _Extension:
    def __init__(self, event_sink=None):
        self.event_sink = event_sink
        self.candidate_lifecycle = None


def _coordinator():
    store = _Store()
    return SimpleNamespace(
        store=store,
        policy_candidates=None,
        evolution_extension=None,
    )


def test_composition_is_idempotent_and_wires_candidate_lifecycle():
    coordinator = _coordinator()
    extension = _Extension()

    first = compose_evolution_extension(coordinator, extension=extension)
    second = compose_evolution_extension(coordinator, extension=_Extension())

    assert first is extension
    assert second is extension
    assert extension.candidate_lifecycle.store is coordinator.store


def test_missing_optional_distribution_is_noop():
    coordinator = _coordinator()
    assert compose_evolution_extension(coordinator) is None
    assert coordinator.evolution_extension is None


def test_event_sink_is_recorded_and_forwarded():
    coordinator = _coordinator()
    received = []
    extension = _Extension(event_sink=lambda *args: received.append(args))

    compose_evolution_extension(coordinator, extension=extension)
    extension.event_sink("candidate_proposed", "candidate-1", {"method_id": "evophy"})

    assert received[0][0] == "candidate_proposed"
    assert coordinator.store.events[0][0] == "candidate_proposed"
