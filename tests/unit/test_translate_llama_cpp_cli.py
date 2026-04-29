"""Unit tests for llama.cpp CLI exposure."""

import importlib


translate = importlib.import_module("translate")


def test_build_parser_accepts_llama_cpp_provider():
    """The CLI parser should expose llama.cpp as a dedicated provider choice."""
    parser = translate.build_parser()

    args = parser.parse_args([
        "-i", "book.txt",
        "--provider", "llama_cpp",
    ])

    assert args.provider == "llama_cpp"
