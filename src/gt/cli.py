from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from . import __version__
from . import github as gh
from . import keychain as kc
from . import config as cfg
from . import todoist as td
from .util import log_debug, strip_markdown, open_url

def build_main_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gh gt", description="Create Todoist task(s) from GitHub issue(s)")
    p.add_argument("numbers", type=int, nargs="+", help="GitHub issue number(s)")
    p.add_argument("--repo", dest="repo", help="Use a specific repository owner/repo instead of cwd")
    p.add_argument("--project-id", dest="project_id")
    p.add_argument("--section-id", dest="section_id")
    p.add_argument("--priority", dest="priority", type=int, choices=[1, 2, 3, 4])
    p.add_argument("--due", dest="due")
    p.add_argument("--labels-as-tags", dest="labels_as_tags", action="store_true")
    p.add_argument("--strip-markdown", dest="strip_md", action="store_true")
    p.add_argument("--open", dest="open_after", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true", help="Show brief progress and backend info")
    p.add_argument("-V", "--version", action="version", version=f"gh-gt {__version__}")
    return p


def build_auth_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gh gt auth", description="Manage Todoist auth token")
    sub = p.add_subparsers(dest="auth_cmd")

    td = sub.add_parser("todoist", help="Set/Save Todoist token")
    td.add_argument("--token", help="Todoist API token to save (optional; prompts if omitted)")
    td.add_argument("--save", choices=["keychain", "file"], default="keychain")

    sub.add_parser("unset", help="Delete stored Todoist token")
    sub.add_parser("show", help="Show token storage status")
    return p


def build_config_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gh gt config", description="Configure gh-gt defaults")
    sub = p.add_subparsers(dest="cfg_cmd")
    proj = sub.add_parser("project", help="Select and save default Todoist project")
    proj.add_argument("--clear", action="store_true", help="Clear default project")
    return p


def run_auth(args: argparse.Namespace) -> int:
    if args.auth_cmd == "todoist":
        token = args.token
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
        if not token and not interactive:
            print("Error: --token is required in non-interactive mode", file=sys.stderr)
            return 2
        if not token:
            import getpass

            print("Todoist API 토큰을 입력하세요.")
            token = getpass.getpass("토큰: ").strip()
            if not token:
                print("Error: 빈 토큰", file=sys.stderr)
                return 2
            try:
                choice = (input("저장 위치를 선택하세요: 키체인(K) / 파일(f) [K/f]: ") or "K").strip().lower()
            except EOFError:
                choice = "k"
            save_target = "keychain" if choice in ("", "k", "keychain") else "file"
        else:
            save_target = args.save or "keychain"

        ok, msg = kc.save_token(token, where=save_target)
        print(msg)
        if ok and sys.stdin.isatty() and sys.stdout.isatty():
            # Offer to set default project now
            try:
                ans = (input("기본 Todoist 프로젝트를 설정할까요? [Y/n]: ") or "y").strip().lower()
            except EOFError:
                ans = "y"
            if ans in ("y", "yes", ""):
                return run_config_project_interactive(clear=False)
        return 0 if ok else 1


def run_config_project_interactive(clear: bool, *, show_backend: bool = False) -> int:
    if clear:
        cfg.set_default_project_id(None)
        print("default project cleared")
        return 0
    try:
        client = td.TodoistClient()
        projects = client.list_projects()
        if show_backend:
            sys.stderr.write(f"Using Todoist {client.last_backend()}\n")
        if not projects:
            print("No projects found in Todoist", file=sys.stderr)
            return 1
        print("프로젝트를 선택하세요:")
        for idx, p in enumerate(projects, 1):
            print(f"  {idx}. {p['name']} ({p['id']})")
        while True:
            try:
                choice = input("번호 입력: ").strip()
            except EOFError:
                choice = ""
            if not choice:
                print("취소됨")
                return 1
            if choice.isdigit():
                i = int(choice)
                if 1 <= i <= len(projects):
                    sel = projects[i - 1]
                    cfg.set_default_project_id(sel["id"])
                    print(f"기본 프로젝트 설정: {sel['name']} ({sel['id']})")
                    return 0
            print("잘못된 입력입니다. 다시 시도하세요.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def run_config(args: argparse.Namespace, *, show_backend: bool = False) -> int:
    if args.cfg_cmd == "project":
        return run_config_project_interactive(clear=args.clear, show_backend=show_backend)
    print("Usage: gh gt config project [--clear]", file=sys.stderr)
    return 2
    if args.auth_cmd == "unset":
        for m in unset_token():
            print(m)
        return 0
    if args.auth_cmd == "show":
        print(show_status())
        return 0
    # Default if user runs `gh gt auth` without subcmd
    print("Usage: gh gt auth [todoist|unset|show] ...", file=sys.stderr)
    return 2


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]

    # Detect top-level subcommands (auth/config)
    if argv and argv[0] == "auth":
        auth_parser = build_auth_parser()
        auth_args = auth_parser.parse_args(argv[1:])
        return run_auth(auth_args)
    if argv and argv[0] == "config":
        cfg_parser = build_config_parser()
        cfg_args = cfg_parser.parse_args(argv[1:])
        # Allow leading -v/--verbose before subcommand
        show_backend = False
        for a in argv:
            if a in ("-v", "--verbose"):
                show_backend = True
                break
        return run_config(cfg_args, show_backend=show_backend)

    parser = build_main_parser()
    args = parser.parse_args(argv)

    try:
        repo = gh.resolve_repo(args.repo)

        # Ensure token present; if missing and interactive, prompt and save
        token = kc.get_token()
        if not token and sys.stdin.isatty() and sys.stdout.isatty():
            import getpass

            print("Todoist API 토큰이 필요합니다.")
            token = getpass.getpass("토큰 입력: ").strip()
            if not token:
                raise RuntimeError("no token provided")
            try:
                choice = (input("토큰을 어디에 저장할까요? 키체인(K) / 파일(f) [K/f]: ") or "K").strip().lower()
            except EOFError:
                choice = "k"
            target = "keychain" if choice in ("", "k", "keychain") else "file"
            ok, msg = kc.save_token(token, where=target)
            print(msg)

        client = td.TodoistClient(token=token)
        if args.verbose:
            sys.stderr.write(f"Using Todoist {client.last_backend()}\n")
        # Default project if not provided
        project_id = args.project_id or cfg.get_default_project_id()

        for num in args.numbers:
            issue = gh.fetch_issue(repo, num)

            body = issue.body or ""
            if args.strip_md and body:
                body = strip_markdown(body)

            description = body.strip()
            if description:
                description += "\n\n" + issue.html_url
            else:
                description = issue.html_url

            content = f"#{issue.number} {issue.title}"

            labels = None
            if args.labels_as_tags and issue.labels:
                labels = issue.labels

            task = client.add_task(
                content=content,
                description=description,
                project_id=project_id,
                section_id=args.section_id,
                priority=args.priority,
                due_string=args.due,
                labels=labels,
            )

            print(f"created: {task.id} - {task.content}")
            if task.url:
                print(task.url)
                if args.open_after:
                    open_url(task.url)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
