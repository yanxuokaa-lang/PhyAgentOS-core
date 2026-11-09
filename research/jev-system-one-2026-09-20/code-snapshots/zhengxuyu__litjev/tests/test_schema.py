import pytest

from litjev.schema import Choice, DecisionSchema, Noul, Score


def test_canonical_types_and_structured_content():
    schema = DecisionSchema(
        {
            "pick": Choice(instructions=["Choose"], criteria={"long key": None, "B": {"value": 2}}),
            "rate": Score(instructions=None, criteria=[None, "High"]),
            "yes": Noul(instructions="Is it?", criteria={"true": "Yes"}),
        }
    )
    assert schema["pick"].choices == ("long key", "B")
    assert schema["rate"].choices == ("0", "1")
    assert schema["yes"].choices == ("false", "true")
    assert DecisionSchema.from_mapping(schema.to_mapping()).to_mapping() == schema.to_mapping()


def test_schema_limits():
    assert len(Choice(criteria={str(i): None for i in range(255)}).choices) == 255
    with pytest.raises(ValueError):
        Choice(criteria={str(i): None for i in range(256)})
    with pytest.raises(ValueError):
        Score(criteria=[None] * 11)
    with pytest.raises(ValueError):
        DecisionSchema({})
