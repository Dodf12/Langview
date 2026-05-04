#!/usr/bin/env python3
"""langview — show GitHub-style language breakdown for a Git project."""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

'''
The subprocess library is used to run outside programs,
and system commands from python.
'''

# Language → (display name, ANSI 256-color code)
LANG_COLORS: dict[str, tuple[str, int]] = {
    ".py":    ("Python",     33),   # blue
    ".ts":    ("TypeScript", 68),   # steel blue
    ".tsx":   ("TypeScript", 68),
    ".js":    ("JavaScript", 220),  # yellow
    ".jsx":   ("JavaScript", 220),
    ".rs":    ("Rust",       166),  # orange-red
    ".go":    ("Go",         81),   # cyan
    ".c":     ("C",          24),   # dark blue
    ".h":     ("C",          24),
    ".cpp":   ("C++",        140),  # purple
    ".cc":    ("C++",        140),
    ".cxx":   ("C++",        140),
    ".hpp":   ("C++",        140),
    ".java":  ("Java",       136),  # amber
    ".kt":    ("Kotlin",     135),  # violet
    ".swift": ("Swift",      203),  # coral
    ".rb":    ("Ruby",       160),  # red
    ".php":   ("PHP",        99),   # mauve
    ".cs":    ("C#",         22),   # dark green
    ".sh":    ("Shell",      148),  # yellow-green
    ".bash":  ("Shell",      148),
    ".zsh":   ("Shell",      148),
    ".html":  ("HTML",       202),  # orange
    ".htm":   ("HTML",       202),
    ".css":   ("CSS",        62),   # medium blue
    ".scss":  ("SCSS",       162),  # pink
    ".sass":  ("SCSS",       162),
    ".json":  ("JSON",       178),  # gold
    ".yaml":  ("YAML",       178),
    ".yml":   ("YAML",       178),
    ".toml":  ("TOML",       130),  # brown
    ".md":    ("Markdown",   252),  # light gray
    ".r":     ("R",          26),   # blue
    ".R":     ("R",          26),
    ".jl":    ("Julia",      63),   # violet-blue
    ".lua":   ("Lua",        18),   # navy
    ".ex":    ("Elixir",     55),   # dark violet
    ".exs":   ("Elixir",     55),
    ".erl":   ("Erlang",     124),  # dark red
    ".hs":    ("Haskell",    97),   # purple
    ".ml":    ("OCaml",      214),  # amber-orange
    ".mli":   ("OCaml",      214),
    ".dart":  ("Dart",       39),   # sky blue
    ".vue":   ("Vue",        41),   # green
    ".svelte":("Svelte",     202),
    ".tf":    ("Terraform",  93),   # purple
    ".mk":    ("Makefile",   64),   # olive green
    "Makefile":("Makefile",  64),
    "makefile":("Makefile",  64),
    ".dtrace":("DTrace",     244),  # gray
    ".d":     ("DTrace",     244),
    ".txt":   ("Text",       252),  # light gray,
    ".tex":   ("TeX",        281),  # light purple
}

# Extensions/names to skip entirely
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "vendor", ".mypy_cache", ".pytest_cache",
}
SKIP_EXTS = {".lock", ".sum", ".min.js", ".map"}
SKIP_FILES = {"package-lock.json", "yarn.lock", "poetry.lock", "Cargo.lock"}


def git_files(root: Path) -> list[Path]:
    '''
    Get a list of files that git tracks or recognizes as untrackeed, excluding ignored files.

    '''
    
    #Reason we are trying is if there is not git, it will return an error
    # and we can catch that and return an empty list, which signals to the caller to fallback to walking the filesystem.
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root, stderr=subprocess.DEVNULL, text=True,
        )
        # The output is a list of file paths relative to the root, one per line.
        return [root / p for p in out.splitlines() if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


'''
This program defins a function walk_files that recursively walks the directory
tree starting from a given root path, and collects all file paths while 
skipping certain directories and file types. It uses os.walk to traverse the filesystem, 
and filters out directories and files based on predefined sets of names and extensions to skip. The resulting list of file paths is returned for further processing.
'''
def walk_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            files.append(Path(dirpath) / name)
    return files

'''
This function takes a file path, and classifies it based on the file name and extension

'''
def classify(path: Path) -> str | None:
    name = path.name
    if name in SKIP_FILES:
        return None
    # Check full name first (e.g., "Makefile")
    if name in LANG_COLORS:
        return name
    ext = path.suffix.lower()
    if not ext or ext in SKIP_EXTS:
        return None
    return ext if ext in LANG_COLORS else None

'''
This function gets a list of file paths, and counts the byte size for each langauge based on the file extensions.
It uses teh classify function to find teh language for each file and sums up sizes fo each language.
'''
def count_bytes(files: list[Path]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for f in files:
        key = classify(f)
        if key is None:
            continue
        try: 
            size = f.stat().st_size
        except OSError:
            size = 0
        if size == 0:
            continue
        lang = LANG_COLORS[key][0]
        totals[lang] = totals.get(lang, 0) + size
    return totals


'''
This function takes a language name and a text string, 
and returns the text wrapped in ANSI escape codes to set the background color according to the 
language's assigned color code. It uses the ANSI 256-color mode to specify the color, and resets the 
formatting at the end of the string.
'''
def ansi_bg(color_code: int, text: str) -> str:
    return f"\x1b[48;5;{color_code}m{text}\x1b[0m"


def ansi_fg(color_code: int, text: str) -> str:
    return f"\x1b[38;5;{color_code}m{text}\x1b[0m"


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def visible_len(s: str) -> int:
    return len(_ANSI_RE.sub("", s))

'''
Finds teh color for the given language name and if not found, defaults to gray
'''
def color_for_lang(lang: str) -> int:
    for _, (name, code) in LANG_COLORS.items():
        if name == lang:
            return code
    return 244  # fallback gray

'''
This function gets a dictionary of the language totals, and bar width and renders a horizntal bar given teh proportion
of each language.
'''
def render_bar(totals: dict[str, int], bar_width: int = 60) -> None:
    grand = sum(totals.values())
    if grand == 0:
        print("No recognized source files found.")
        return

    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)

    # Build the bar
    bar_chars: list[str] = []
    assigned = 0
    for i, (lang, size) in enumerate(ranked):
        pct = size / grand
        # Last entry gets remaining chars to avoid rounding gaps
        if i == len(ranked) - 1:
            width = bar_width - assigned
        else:
            width = round(pct * bar_width)
        if width < 1:
            width = 1
        assigned += width
        bar_chars.append(ansi_bg(color_for_lang(lang), " " * width))

    print()
    print("  \x1b[1mLanguages\x1b[0m")
    print()
    print("  " + "".join(bar_chars))
    print()

    # Legend — two columns
    entries = []
    for lang, size in ranked:
        pct = size / grand * 100
        dot = ansi_fg(color_for_lang(lang), "●")
        entries.append(f"{dot} \x1b[1m{lang}\x1b[0m {pct:.1f}%")

    col_width = max(visible_len(e) for e in entries) + 4 if entries else 24
    col = 0
    for entry in entries:
        if col == 0:
            print("  " + entry + " " * (col_width - visible_len(entry)), end="")
            col = 1
        else:
            print(entry)
            col = 0
    if col == 1:
        print()
    print()


def print_help() -> None:
    b = "\x1b[1m"       # bold
    r = "\x1b[0m"       # reset
    dim = "\x1b[2m"     # dim

    print(f"""
{b}langview{r} — GitHub-style language bar for any Git project

{b}USAGE{r}
  langview {dim}[path] [options]{r}

{b}ARGUMENTS{r}
  {b}path{r}    Directory to scan {dim}(default: current directory){r}

{b}OPTIONS{r}
  {b}--width N{r}   Width of the language bar in characters {dim}(default: 60){r}
  {b}--walk{r}      Scan all files instead of only git-tracked files
  {b}--langs{r}     List all recognized languages and their colors
  {b}-h, --help{r}  Show this help message

{b}EXAMPLES{r}
  langview                          {dim}# scan current git repo{r}
  langview ~/projects/my-app        {dim}# scan a specific project{r}
  langview ~/projects/my-app --width 80
  langview ~/projects/my-app --walk {dim}# include untracked files{r}
  langview --langs                  {dim}# show all supported languages{r}
""")


def print_langs() -> None:
    b = "\x1b[1m"
    r = "\x1b[0m"
    print(f"\n{b}Supported languages:{r}\n")
    seen: set[str] = set()
    langs = []
    for _, (name, code) in LANG_COLORS.items():
        if name not in seen:
            seen.add(name)
            langs.append((name, code))
    langs.sort(key=lambda x: x[0])
    entries = []
    for name, code in langs:
        dot = ansi_fg(code, "●")
        entries.append(f"  {dot} {b}{name}{r}")

    col_width = max(visible_len(e) for e in entries) + 4 if entries else 24
    col = 0
    for entry in entries:
        if col == 0:
            print(entry + " " * (col_width - visible_len(entry)), end="")
            col = 1
        else:
            print(entry)
            col = 0
    if col == 1:
        print()
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="langview",
        description="Show a GitHub-style language breakdown for a Git project.",
        add_help=False,
    )

    # The following lines add arguments to the parser
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the Git repository (default: current directory)",
    )

    #This line adds an optional argument --width to the CLI, which allows the user to specify the
    #  width of the language bar in characters.
    parser.add_argument(
        "--width",
        type=int,
        default=60,
        help="Width of the language bar in characters (default: 60)",
    )

    # This line adds a flag --walk to the CLI tool and if the user includes this flag, 
    #the program will walk the filesystem isntead of using git ls-files
    parser.add_argument(
        "--walk",
        action="store_true",
        help="Walk the filesystem instead of using git ls-files",
    )
    parser.add_argument(
        "--langs",
        action="store_true",
        help="List all recognized languages and their colors",
    )
    parser.add_argument(
        "-h", "--help",
        action="store_true",
        help="Show this help message",
    )
    args = parser.parse_args()

    if args.help:
        print_help()
        sys.exit(0)

    if args.langs:
        print_langs()
        sys.exit(0)

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"Error: '{root}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    if args.walk:
        files = walk_files(root)
    else:
        files = git_files(root)
        if not files:
            # Fallback: not a git repo or no tracked files
            files = walk_files(root)

    totals = count_bytes(files)
    render_bar(totals, bar_width=args.width)


if __name__ == "__main__":
    main()
