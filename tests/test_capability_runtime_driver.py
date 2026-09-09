import pytest

from PhyAgentOS.forge.capability_runtime import (
    ActionAdmission,
    CapabilityRuntime,
    CapabilityRuntimeError,
)


class Driver:
    def __init__(self):
        self.result = None
        self.cancels = 0

    def poll(self):
        return self.result

    def cancel(self):
        self.cancels += 1

    def stop(self):
        self.cancel()


class Endpoint:
    def __init__(self, driver):
        self.driver = driver

    def admit(self, arguments):
        return ActionAdmission(start=lambda invocation, attempt: ActionAdmission(driver=self.driver))


def runtime(driver, clock=lambda: 0):
    value = CapabilityRuntime(clock=clock)
    value.register_tool({"tool_id": "move", "endpoint_id": "arm", "operation": "move", "semantics": "action"}, Endpoint(driver))
    return value


def test_cancel_reaches_provider_immediately_and_waits_for_confirmation():
    driver = Driver()
    value = runtime(driver)
    key = value.start_action("move")["invocation_id"]
    assert value.cancel_invocation(key)["accepted"] is True
    assert driver.cancels == 1
    assert value.invocation_status(key)["status"] == "cancel_requested"
    driver.result = {"status": "cancelled", "world_change_started": True, "outcome_known": True, "stop_confirmed": True}
    assert value.invocation_result(key)["status"] == "cancelled"
    assert driver.cancels == 1


def test_timeout_retains_running_driver_and_can_reconcile_later():
    now = [0]
    driver = Driver()
    value = runtime(driver, lambda: now[0])
    key = value.start_action("move", timeout_ms=100)["invocation_id"]
    now[0] = 1
    assert value.invocation_result(key)["status"] == "unknown"
    assert driver.cancels == 1
    with pytest.raises(CapabilityRuntimeError, match="concurrency"):
        value.start_action("move")
    driver.result = {"status": "cancelled", "world_change_started": True, "outcome_known": True}
    assert value.invocation_result(key)["status"] == "cancelled"


def test_timeout_overrides_nested_success_summary():
    class Static:
        def admit(self, arguments):
            return ActionAdmission(pending_polls=5, terminal_result={"capability_outcome_summary": {"status": "succeeded", "outcome_known": True, "artifact_refs": ["partial"]}})
    now = [0]
    value = CapabilityRuntime(clock=lambda: now[0])
    value.register_tool({"tool_id": "move", "endpoint_id": "arm", "operation": "move", "semantics": "action"}, Static())
    key = value.start_action("move", timeout_ms=1)["invocation_id"]
    now[0] = 1
    summary = value.invocation_result(key)["result"]["capability_outcome_summary"]
    assert summary["status"] == "unknown"
    assert summary["outcome_known"] is False
    assert summary["artifact_refs"] == ["partial"]
