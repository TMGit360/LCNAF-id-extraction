#!/usr/bin/env python3
"""Extract LCNAF identifiers from an N-Triples authority dump into batched CSVs.

Identifiers are taken from the record delimiter comments that begin each record,
e.g.:

    # BEGIN /authorities/names/n00020848

which yields the identifier ``n00020848``.

The export path is used as a base name: a folder of that name is created and the
identifiers are written into it as numbered CSV files of 100 rows each, every
file carrying its own ``LCNAF`` header. Entering ``lcnaf_ids.csv`` produces:

    lcnaf_ids/lcnaf_ids_001.csv
    lcnaf_ids/lcnaf_ids_002.csv
    ...

Run with no arguments and it prompts for the paths, then offers to extract
another file when the export finishes; 'q' quits at any prompt.

Usage:
    python3 lcnaf_extract.py                       # prompts, repeats until 'q'
    python3 lcnaf_extract.py INPUT OUTPUT          # one extraction, no prompts
    python3 lcnaf_extract.py INPUT OUTPUT --batch-size 250
"""

import argparse
import csv
import glob
import os
import re
import sys

DEFAULT_BATCH_SIZE = 100
QUIT_ANSWERS = ("q", "quit")

# "# BEGIN /authorities/names/n00020848" -> "n00020848"
# Tolerates a leading http://id.loc.gov host and any authority scheme segment.
BEGIN_RE = re.compile(
    r"^\s*#\s*BEGIN\s+"
    r"(?:https?://[^\s/]+)?"
    r"/authorities/[^/\s]+/"
    r"(?P<lcnaf>[^\s/]+)\s*$",
    re.IGNORECASE,
)


def clean_path(raw):
    """Normalize a path typed at a prompt (strip quotes, expand ~ and $VARS)."""
    path = raw.strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in ("'", '"'):
        path = path[1:-1]
    return os.path.expanduser(os.path.expandvars(path.strip()))


class QuitRequested(Exception):
    """Raised when the user answers a prompt with 'q'."""


def prompt_path(message, validate):
    """Prompt until `validate` accepts the entered path; returns the path.

    Entering 'q' at any prompt quits instead.
    """
    while True:
        try:
            answer = input(message)
        except EOFError:
            raise QuitRequested()
        if answer.strip().lower() in QUIT_ANSWERS:
            raise QuitRequested()
        path = clean_path(answer)
        if not path:
            print("A path is required.", file=sys.stderr)
            continue
        problem = validate(path)
        if problem is None:
            return path
        print(problem, file=sys.stderr)


def check_input(path):
    if not os.path.exists(path):
        return "No such file: %s" % path
    if os.path.isdir(path):
        return "That is a directory, not a file: %s" % path
    if not os.access(path, os.R_OK):
        return "File is not readable: %s" % path
    return None


def export_folder(export_path):
    """Folder that will hold the batch files, derived from the export path."""
    export_path = export_path.rstrip(os.sep)
    root, ext = os.path.splitext(export_path)
    # "reports/lcnaf_ids.csv" -> "reports/lcnaf_ids"; "reports/batches" -> itself
    return root if ext.lower() == ".csv" else export_path


def check_export(path):
    folder = export_folder(path)
    if not os.path.basename(folder):
        return "Please include a name for the export, not just a directory."
    if os.path.exists(folder) and not os.path.isdir(folder):
        return "A file already exists at %s; choose another name." % folder
    parent = os.path.dirname(os.path.abspath(folder))
    if not os.path.isdir(parent):
        return "No such directory: %s" % parent
    if not os.access(parent, os.W_OK):
        return "Directory is not writable: %s" % parent
    return None


def extract_ids(input_path):
    """Yield LCNAF identifiers in the order they appear in the file."""
    with open(input_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if "BEGIN" not in line:          # cheap pre-filter for large files
                continue
            match = BEGIN_RE.match(line)
            if match:
                yield match.group("lcnaf")


def existing_batches(folder, stem):
    """Batch files already sitting in the export folder, if any."""
    return sorted(glob.glob(os.path.join(folder, "%s_[0-9]*.csv" % stem)))


def write_batches(folder, stem, ids, batch_size):
    """Write ids into folder/stem_NNN.csv files of batch_size rows each.

    Every file repeats the 'LCNAF' header. Returns the list of paths written.
    """
    os.makedirs(folder, exist_ok=True)
    batch_count = (len(ids) + batch_size - 1) // batch_size
    width = max(3, len(str(batch_count)))
    written = []

    for index in range(batch_count):
        chunk = ids[index * batch_size:(index + 1) * batch_size]
        path = os.path.join(folder, "%s_%0*d.csv" % (stem, width, index + 1))
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["LCNAF"])
            for lcnaf in chunk:
                writer.writerow([lcnaf])
        written.append(path)

    return written


def confirm(message, force):
    """Ask before clobbering a previous export; --force answers yes."""
    if force:
        return True
    if not sys.stdin.isatty():
        print("%s Re-run with --force to overwrite." % message, file=sys.stderr)
        return False
    try:
        return input("%s Overwrite? [y/N] " % message).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def ask_continue():
    """After an export, offer another extraction. True to keep going."""
    while True:
        try:
            answer = input(
                "\nExtract another file? Enter q to quit, "
                "or press Enter to continue: "
            ).strip().lower()
        except EOFError:
            return False
        if answer in QUIT_ANSWERS:
            return False
        if answer in ("", "y", "yes", "c", "continue"):
            return True
        print("Please press Enter to continue, or enter q to quit.",
              file=sys.stderr)


def run_extraction(input_path, export_path, batch_size, force):
    """Extract one file into a folder of batched CSVs. Returns an exit code."""
    folder = export_folder(export_path)
    stem = os.path.basename(folder)

    try:
        ids = list(extract_ids(input_path))
    except OSError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1

    if not ids:
        print("No LCNAF identifiers found in %s; nothing exported." % input_path)
        return 0

    stale = existing_batches(folder, stem)
    if stale:
        if not confirm("%s already holds %d %s_NNN.csv file(s)."
                       % (folder, len(stale), stem), force):
            print("Cancelled; nothing written.")
            return 1
        for path in stale:
            os.remove(path)

    try:
        written = write_batches(folder, stem, ids, batch_size)
    except OSError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1

    last_rows = len(ids) - batch_size * (len(written) - 1)
    print("Extracted %d LCNAF identifiers into %d file(s) in %s"
          % (len(ids), len(written), folder))
    if len(written) == 1:
        print("  %s (%d rows)" % (os.path.basename(written[0]), last_rows))
    else:
        print("  %s ... %s (%d rows each, last file has %d)"
              % (os.path.basename(written[0]), os.path.basename(written[-1]),
                 batch_size, last_rows))

    unique = len(set(ids))
    if unique != len(ids):
        repeats = len(ids) - unique
        print("Note: %d %s a repeat of an earlier identifier (%d unique)."
              % (repeats, "row is" if repeats == 1 else "rows are", unique))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract LCNAF identifiers from an authority file into "
                    "batched CSV files inside a folder."
    )
    parser.add_argument("input", nargs="?", help="file to extract identifiers from")
    parser.add_argument("output", nargs="?",
                        help="export name; a folder of this name holds the CSVs")
    parser.add_argument("-n", "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        metavar="N",
                        help="rows per CSV file (default: %d)" % DEFAULT_BATCH_SIZE)
    parser.add_argument("-f", "--force", action="store_true",
                        help="replace an existing export without asking")
    args = parser.parse_args(argv)

    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    # Paths given on the command line: one extraction, no prompts.
    if args.input or args.output:
        if not (args.input and args.output):
            parser.error("give both an input file and an export name, or neither")
        input_path = clean_path(args.input)
        problem = check_input(input_path)
        if problem:
            parser.error(problem)
        export_path = clean_path(args.output)
        problem = check_export(export_path)
        if problem:
            parser.error(problem)
        return run_extraction(input_path, export_path, args.batch_size, args.force)

    print("LCNAF ID Extraction Tool\n")
    status = 0
    while True:
        try:
            input_path = prompt_path(
                "Enter directory and file name for extraction: ", check_input
            )
            export_path = prompt_path(
                "\nEnter directory and file name for .csv export: ", check_export
            )
        except QuitRequested:
            break
        status = run_extraction(input_path, export_path,
                                args.batch_size, args.force)
        if not ask_continue():
            break
        print()

    print("\nDone.")
    return status


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
