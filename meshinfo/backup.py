"""Functionality for exporting and importing application data."""

from __future__ import annotations

import re
import shutil
import subprocess
import tarfile
from collections import Counter
from collections.abc import Iterator
from multiprocessing.pool import Pool
from pathlib import Path
from tempfile import TemporaryDirectory

import rrdtool
import structlog

logger = structlog.get_logger()


def export_data(
    data_dir: Path,
    archive: Path,
) -> str | None:
    """Export RRD files and SQLite database to archive file."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with Pool() as pool:
            results = pool.starmap(_export_file, _list_files(data_dir, temp_path))
        count = Counter(results)

        # Python's tarfile is very slow, use system `tar` when available
        if shutil.which("tar"):
            files = [item.name for item in temp_path.iterdir()]
            subprocess.run(
                ("tar", "-czf", str(archive.resolve()), *files),
                check=True,
                cwd=temp_dir,
            )
            count["archived"] = len(files)
        else:
            with tarfile.open(archive, "x:gz") as f:
                for filename in temp_path.iterdir():
                    count["archived"] += 1
                    f.add(filename, arcname=filename.name)

    print(
        f"Exported {count['archived']:,d} items: "
        f"{count['rrd']:,d} RRD files, "
        f"{count['copied']:,d} other files, "
        f"{count['skipped']:,d} skipped directories"
    )
    return None


def _list_files(path: Path, destination: Path) -> Iterator[tuple[Path, Path]]:
    """Yield files (recursively) and the corresponding destination folder.

    Used for listing the files to import/export.
    Creates the destination directory if it does not exist.

    """
    if not destination.exists():
        destination.mkdir(parents=True)
    for item in path.iterdir():
        if item.is_dir():
            yield from _list_files(item, destination / item.name)
        else:
            yield item, destination


def _export_file(filename: Path, destination: Path) -> str:
    """Exports a single file for the export process."""
    if filename.is_dir():
        raise RuntimeError("Directories should have been walked.")
    if filename.suffix == ".rrd":
        logger.debug("Dumping for export", filename=filename)
        rrdtool.dump(str(filename), str(destination / f"{filename.stem}.xml"))
        return "rrd"
    logger.debug("Copying for export", filename=filename)
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
        temp_path = Path(temp_dir)
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
                        logger.warning("Invalid filename in archive", name=item.name)
                        continue
                    count["extracted"] += 1
                    f.extract(item, temp_dir, set_attrs=False)
        with Pool() as pool:
            results = pool.starmap(_import_file, _list_files(temp_path, data_dir))
        count.update(results)

    print(
        f"Imported {count['extracted']:,d} items: "
        f"{count['rrd']:,d} RRD files, {count['copied']:,d} other files"
    )
    return None


def _import_file(filename: Path, destination: Path) -> str:
    """Imports a single file."""
    if filename.suffix == ".xml":
        logger.debug("Converting RRD for import", filename=filename)
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
    logger.debug("Copying for importing", filename=filename)
    shutil.copy(filename, destination)
    return "copied"
