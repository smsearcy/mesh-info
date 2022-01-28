"""Functionality for exporting and importing application data."""
from __future__ import annotations

import os.path
import re
import shutil
import subprocess
import tarfile
from collections import Counter
from functools import partial
from multiprocessing.pool import Pool
from pathlib import Path
from tempfile import TemporaryDirectory

import rrdtool
from loguru import logger


def export_data(
    data_dir: Path,
    archive: Path,
) -> str | None:
    """Export RRD files and SQLite database to archive file."""
    with TemporaryDirectory() as temp_dir:
        export_file = partial(_export_file, destination=temp_dir)
        with Pool() as pool:
            results = pool.map(export_file, data_dir.iterdir())
        count = Counter(results)

        # Python's tarfile is very slow, use system `tar` when available
        if shutil.which("tar"):
            files = [item.name for item in Path(temp_dir).iterdir()]
            subprocess.run(
                ("tar", "-czf", str(archive.resolve()), *files),
                check=True,
                cwd=temp_dir,
            )
            count["archived"] = len(files)
        else:
            with tarfile.open(archive, "x:gz") as f:
                for filename in Path(temp_dir).iterdir():
                    count["archived"] += 1
                    f.add(filename, arcname=filename.name)

    print(
        f"Exported {count['archived']:,d} items: "
        f"{count['rrd']:,d} RRD files, "
        f"{count['copied']:,d} other files, "
        f"{count['skipped']:,d} skipped directories"
    )
    return None


def _export_file(filename: Path, destination: str) -> str:
    """Exports a single file for the export process."""
    if filename.suffix == ".rrd":
        logger.debug("Dumping {} for export", filename)
        rrdtool.dump(str(filename), os.path.join(destination, f"{filename.stem}.xml"))
        return "rrd"
    elif filename.is_dir():
        # assuming for now that sub-folders shouldn't be exported (cache?)
        return "skipped"
    else:
        logger.debug("Exporting {}", filename)
        shutil.copy(filename, destination)
        return "copied"


def import_data(
    archive: Path,
    data_dir: Path,
) -> str | None:
    """Import RRD files and SQLite database from archive file."""
    if not shutil.which("rrdtool"):
        return "Data import requires 'rrdtool' to be available on the command line."
    count: Counter[str] = Counter()
    with TemporaryDirectory() as temp_dir:
        # Python's tarfile is very slow, use system `tar` when available
        if shutil.which("tar"):
            subprocess.run(
                ("tar", "-xzf", str(archive.resolve())),
                check=True,
                cwd=temp_dir,
            )
            count["extracted"] = sum(1 for _ in Path(temp_dir).iterdir())
        else:
            with tarfile.open(archive, "r:*") as f:
                for item in f.getmembers():
                    if not re.match(r"\w", item.name):
                        logger.warning("Invalid filename in archive: '{}'", item.name)
                        continue
                    count["extracted"] += 1
                    f.extract(item, temp_dir, set_attrs=False)
        import_file = partial(_import_file, destination=data_dir)
        with Pool() as pool:
            results = pool.map(import_file, Path(temp_dir).iterdir())
        count.update(results)

    print(
        f"Imported {count['extracted']:,d} items: "
        f"{count['rrd']:,d} RRD files, {count['copied']:,d} other files"
    )
    return None


def _import_file(filename: Path, destination: Path) -> str:
    """Imports a single file."""
    if filename.suffix == ".xml":
        logger.debug("Converting {} for import", filename)
        subprocess.run(
            (
                "rrdtool",
                "restore",
                str(filename),
                str(destination / f"{filename.stem}.rrd"),
            ),
            check=True,
        )
        return "rrd"
    else:
        logger.debug("Importing {}", filename)
        shutil.copy(filename, destination)
        return "copied"
