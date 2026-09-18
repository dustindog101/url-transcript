"""CLI entrypoint for url-transcript / ut."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import (
    EXIT_ASR,
    EXIT_BAD_URL,
    EXIT_DEPS,
    EXIT_DOWNLOAD,
    EXIT_OK,
    __version__,
    asr_parakeet,
    doctor,
    download,
    pipeline,
)
from .asr_whisper import WhisperError
from .urls import UnsupportedURLError


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ut",
        description="URL → transcript (TikTok / YouTube / Instagram). Clean text on stdout.",
    )
    p.add_argument("-V", "--version", action="version", version=f"url-transcript {__version__}")
    p.add_argument(
        "url",
        nargs="?",
        help="TikTok / YouTube / Instagram URL (or 'doctor' to check dependencies)",
    )
    p.add_argument("--json", action="store_true", help="Structured JSON on stdout (for agents)")
    p.add_argument("--save", action="store_true", help="Write transcript to ./transcripts/")
    p.add_argument("-o", "--output", metavar="PATH", help="Write transcript to PATH")
    p.add_argument(
        "--engine",
        choices=("auto", "parakeet", "whisper"),
        default="auto",
        help="ASR engine (default: auto = Parakeet then whisper)",
    )
    p.add_argument(
        "--model-version",
        default="v3",
        choices=("v2", "v3", "2", "3"),
        help="Parakeet model version (default: v3)",
    )
    p.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Pass cookies from browser to yt-dlp (firefox recommended for IG)",
    )
    p.add_argument("--cookies", metavar="FILE", help="Netscape cookies.txt for yt-dlp")
    p.add_argument("--keep-audio", action="store_true", help="Keep cached audio file")
    p.add_argument("-v", "--verbose", action="store_true", help="More progress on stderr")
    p.add_argument("-q", "--quiet", action="store_true", help="Suppress progress on stderr")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # `ut doctor` — no argparse conflict with URLs
    if argv and argv[0] == "doctor":
        checks = doctor.run_checks()
        print(doctor.format_report(checks))
        return EXIT_OK if doctor.required_ok(checks) else EXIT_DEPS

    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.url:
        parser.print_help()
        return EXIT_BAD_URL

    verbose = not args.quiet

    mv = args.model_version
    if mv in {"2", "3"}:
        mv = f"v{mv}"

    try:
        result = pipeline.run(
            args.url,
            engine=args.engine,
            model_version=mv,
            cookies_from_browser=args.cookies_from_browser,
            cookies_file=args.cookies,
            keep_audio=args.keep_audio,
            want_captions=args.json,
            verbose=verbose,
        )
    except UnsupportedURLError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_BAD_URL
    except download.DownloadError as e:
        print(f"error: download failed: {e}", file=sys.stderr)
        return EXIT_DOWNLOAD
    except (asr_parakeet.ParakeetError, WhisperError) as e:
        print(f"error: ASR failed: {e}", file=sys.stderr)
        return EXIT_ASR
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "not found" in msg.lower():
            print(f"error: {e}", file=sys.stderr)
            return EXIT_DEPS
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ASR

    if args.output:
        pipeline.save_transcript(result, Path(args.output))
        if verbose:
            print(f">> saved {args.output}", file=sys.stderr)
    elif args.save:
        path = pipeline.default_save_path(result)
        pipeline.save_transcript(result, path)
        if verbose:
            print(f">> saved {path}", file=sys.stderr)

    if args.json:
        print(result.to_json())
    else:
        print(result.transcript)

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
