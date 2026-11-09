"""Export effective independent branch inputs for the restored cached scorer."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from transformers import AutoTokenizer

from litjev.schema import SystemOneRequest
from litjev.slots import compile_slots


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", default="mmlu-request-preview.json")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()
    request = SystemOneRequest.model_validate(
        json.loads(Path(args.input).read_text())["runs"][0]["request"]
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    compiled = compile_slots(
        tokenizer, "Answer each question using its listed options.", request.to_schema()
    )
    directory = Path(args.output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "cached-branch-inputs.json").write_text(
        json.dumps(
            [tokenizer.decode(row) for row in compiled.input_ids], ensure_ascii=False, indent=2
        )
        + "\n"
    )
    (directory / "cached-branch-tokens.json").write_text(
        json.dumps(asdict(compiled), indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "input_tokens": compiled.prefix_length + sum(map(len, compiled.slot_ids)),
                "slot_positions": compiled.positions,
            }
        )
    )


if __name__ == "__main__":
    main()
