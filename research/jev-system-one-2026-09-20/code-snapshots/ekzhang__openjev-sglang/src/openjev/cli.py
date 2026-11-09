import argparse
import asyncio
import json
import logging

from .config import Settings


def main():
    parser = argparse.ArgumentParser(prog="openjev")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser(
        "serve", help="Start the API and SGLang (or connect to an existing backend)"
    )
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--model")
    serve.add_argument("--served-model-name", help="Public model ID, independent of weight source")
    serve.add_argument("--revision")
    serve.add_argument("--frontend", choices=["rust", "python"])
    serve.add_argument("--sglang-python", help="Python in the CUDA/SGLang environment")
    serve.add_argument("--connect", metavar="URL", help="Use an already-running SGLang server")
    serve.add_argument("sglang_args", nargs=argparse.REMAINDER, help="Extra SGLang args after --")
    smoke = sub.add_parser("smoke", help="Test a running server, including 64-way logits")
    smoke.add_argument("url")
    smoke.add_argument("--timeout", type=float, default=1200)
    sub.add_parser("schema", help="Print the OpenAPI schema without loading model weights")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "smoke":
        from .smoke import smoke_test

        print(json.dumps(asyncio.run(smoke_test(args.url, timeout=args.timeout)), indent=2))
        return
    from .api import create_app

    if args.command == "schema":
        print(json.dumps(create_app().openapi(), indent=2))
        return
    overrides = {
        key: getattr(args, key)
        for key in (
            "host",
            "port",
            "model",
            "served_model_name",
            "revision",
            "frontend",
            "sglang_python",
        )
        if getattr(args, key) is not None
    }
    if args.connect:
        overrides["backend_url"] = args.connect.rstrip("/")
    settings = Settings(**overrides)
    extra = args.sglang_args
    if extra[:1] == ["--"]:
        extra = extra[1:]
    import uvicorn

    uvicorn.run(
        create_app(settings, launch_backend=not args.connect, sglang_args=extra),
        host=settings.host,
        port=settings.port,
        loop="uvloop",
        http="httptools",
        access_log=False,
    )
