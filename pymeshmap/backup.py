"""Functionality for exporting and importing application data."""
from __future__ import annotations

import os.path
import re
import shutil
import tarfile
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

import rrdtool
from loguru import logger


def export_data(
    data_dir: Path,
    filename: str,
) -> str | None:
    """Export RRD files and SQLite database to archive file."""
    count: defaultdict[str, int] = defaultdict(int)
    with TemporaryDirectory() as temp_dir:
        for item in data_dir.iterdir():
            if item.suffix == ".rrd":
                count["rrd"] += 1
                logger.debug("Dumping {} for export", item)
                rrdtool.dump(str(item), os.path.join(temp_dir, f"{item.stem}.xml"))
            elif item.is_dir():
                # assuming for now that sub-folders shouldn't be exported (cache?)
                count["skipped"] += 1
                continue
            else:
                count["copied"] += 1
                logger.debug("Exporting {}", item)
                shutil.copy(item, temp_dir)

        with tarfile.open(filename, "x:gz") as f:
            for child in Path(temp_dir).iterdir():
                count["archived"] += 1
                f.add(child, arcname=child.name)

    print(
        f"Exported {count['archived']:,d} items: "
        f"{count['rrd']:,d} RRD files, "
        f"{count['copied']:,d} other files, "
        f"{count['skipped']:,d} skipped directories"
    )
    return None


def import_data(
    filename: str,
    data_dir: Path,
) -> str | None:
    """Import RRD files and SQLite database from archive file."""
    count: defaultdict[str, int] = defaultdict(int)
    with TemporaryDirectory() as temp_dir:
        with tarfile.open(filename, "r:*") as f:
            for item in f.getmembers():
                if not re.match(r"\w", item.name):
                    logger.warning("Invalid filename in archive: '{}'", item.name)
                    continue
                count["extracted"] += 1
                f.extract(item, temp_dir, set_attrs=False)
        for child in Path(temp_dir).iterdir():
            if child.suffix == ".xml":
                logger.debug("Converting {} for import", child)
                rrdtool.restore(str(child), str(data_dir / f"{child.stem}.rrd"))
                count["rrd"] += 1
            else:
                logger.debug("Importing {}", child)
                shutil.copy(child, data_dir)
                count["copied"] += 1
    print(
        f"Imported {count['extracted']:,d} items: "
        f"{count['rrd']:,d} RRD files, {count['copied']:,d} other files"
    )
    return None
