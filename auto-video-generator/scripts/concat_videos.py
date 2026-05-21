#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
from pathlib import Path


def require_tool(name):
    if shutil.which(name) is None:
        raise SystemExit(f"Missing required tool on PATH: {name}")


def run(cmd):
    subprocess.run(cmd, check=True)


def concat(inputs, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    list_file = output.parent / "concat_list.txt"
    list_file.write_text("".join(f"file '{path.resolve().as_posix()}'\n" for path in inputs), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)])


def inputs_from_manifest(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    inputs = [Path(chapter["output"]) for chapter in manifest["chapters"]]
    output = Path(manifest["final_output"])
    return inputs, output


def main():
    parser = argparse.ArgumentParser(description="Concat chapter MP4 files into one final MP4.")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("inputs", nargs="*")
    args = parser.parse_args()

    require_tool("ffmpeg")
    if args.manifest:
        inputs, output = inputs_from_manifest(args.manifest.resolve())
        if args.output:
            output = args.output.resolve()
    else:
        if not args.inputs or not args.output:
            raise SystemExit("Use --manifest or provide inputs plus --output.")
        inputs = [Path(value).resolve() for value in args.inputs]
        output = args.output.resolve()

    missing = [str(path) for path in inputs if not path.exists()]
    if missing:
        raise SystemExit("Missing input videos:\n" + "\n".join(missing))
    concat(inputs, output)
    print(json.dumps({"output": str(output), "inputs": len(inputs)}, indent=2))


if __name__ == "__main__":
    main()
