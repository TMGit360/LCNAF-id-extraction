# LCNAF ID Extraction Tool

An easy-to-use command-line tool that efficiently extracts LCNAF IDs from N-Triples (`.nt`)
NAF files downloaded from <https://id.loc.gov/download/>.

After the input and target directory and files are established, `.csv` files are created,
organized, and placed in a directory. Each `.csv` file contains no more than 100 rows to
support import into OpenRefine.

## Repository contents

| File | Description |
| --- | --- |
| `lcnaf_extract.py` | The tool. Standard-library Python; nothing to install. |
| `examplerecordspreextract.nt` | Example input — 200 name authority records (2.1 MB) in the same N-Triples format as the full downloads from id.loc.gov. Use it to try the tool before pointing it at a real file. |
| `lcnaf_ids/` | Example output — the result of running the tool on the example records. |
| `README.md` | This file. |

## Dependencies

Python 3.6 or newer. The tool uses only the standard library.

## How to use

Open a command line or terminal and run:

```
python3 lcnaf_extract.py
```
Then follow the prompts:

```
LCNAF ID Extraction Tool

Enter directory and file name for extraction: examplerecordspreextract.nt
Enter directory and file name for .csv export: lcnaf_ids.csv
Extracted 5444 LCNAF identifiers into 55 file(s) in lcnaf_ids
  lcnaf_ids_001.csv ... lcnaf_ids_055.csv (100 rows each, last file has 44)

Extract another file? Enter q to quit, or press Enter to continue:
```

Press Enter to extract another file, or enter `q` to quit. `q` also quits at either path
prompt.
## Entering directory paths

The sample session above uses plain file names, which read from and write to the folder you
ran the command in. To work with files elsewhere, type the full path at each prompt:

| Operating system | Extraction (input file) | .csv export (name for the output folder) |
| --- | --- | --- |
| **Windows** | `C:\Users\yourname\Downloads\names.madsrdf.nt` | `C:\Users\yourname\Documents\lcnaf_ids.csv` |
| **macOS & Linux** | `~/Downloads/names.madsrdf.nt` | `~/Documents/lcnaf_ids.csv` |
