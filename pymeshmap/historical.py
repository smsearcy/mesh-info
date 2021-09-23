"""Capture historical data and display it in graphs via RRDtool."""

from __future__ import annotations

import multiprocessing as mp
from itertools import cycle
from pathlib import Path
from typing import Any, Iterable, List, Optional

import attr
import pendulum
import rrdtool
from loguru import logger

from .models import Link, Node

# Archives based on defaults in Munin
ARCHIVES = [
    "RRA:AVERAGE:0.5:1:144",  # 1 day, resolution 5 minutes
    "RRA:MIN:0.5:1:144",
    "RRA:MAX:0.5:1:144",
    "RRA:AVERAGE:0.5:6:432",  # 9 days, resolution 30 minutes
    "RRA:MIN:0.5:6:432",
    "RRA:MAX:0.5:6:432",
    "RRA:AVERAGE:0.5:24:540",  # 45 days, resolution 2 hours
    "RRA:MIN:0.5:24:540",
    "RRA:MAX:0.5:24:540",
    "RRA:AVERAGE:0.5:288:450",  # 450 days, resolution 1 day
    "RRA:MIN:0.5:288:450",
    "RRA:MAX:0.5:288:450",
]
COLORS = ("#0000FF", "#FF00FF", "#00FFFF", "#00FF00")


@attr.s(auto_attribs=True)
class HistoricalStats:
    """Class to wrap historical statistics/data functionality.

    This gives an easy way to persist some basic configuration.  It also means
    we can wrap/abstract some of the common functionality.

    """

    data_path: Path

    def update_node_stats(self, node: Node) -> bool:
        # switch to async after testing!
        rrd_file = self._node_filename(node)

        timestamp = node.last_seen.int_timestamp

        # create RRD file if it doesn't exist
        if not rrd_file.exists():
            _create_node_rrd_file(rrd_file, start=timestamp)

        values = ":".join(
            _dump(v)
            for v in [
                node.link_count,
                len(node.services),
                node.up_time_seconds,
                node.load_averages[0] if isinstance(node.load_averages, list) else None,
                node.radio_link_count,
                node.dtd_link_count,
                node.tunnel_link_count,
            ]
        )
        logger.trace("Updating node stats: {} -> {}", rrd_file.name, values)
        try:
            rrdtool.update(
                str(rrd_file),
                "--template",
                "link_count:service_count:uptime:load:radio_links:dtd_links:tunnel_links",  # noqa
                f"{timestamp}:{values}",
            )
        except rrdtool.OperationalError as exc:
            # TODO: detect errors due to new data points and rebuild data file?
            logger.error("RRDtool error: {}", exc)
            return False
        return True

    def graph_network_stats(
        self, *, start: pendulum.DateTime, end: pendulum.DateTime, title: str = ""
    ) -> bytes:
        """Graph network info."""
        rrd_file = self._network_filename()
        colors = cycle(COLORS)
        graph = Graph(
            title=title or "network stats",
            vertical_label="count",
            start=start,
            end=end,
        )

        for ds in ("node_count", "link_count", "error_count"):
            graph.add_summarized_ds(
                definition=f"DEF:{ds}={rrd_file}:{ds}:AVERAGE",
                v_name=ds,
                color=next(colors),
                style="LINE1",
                legend=ds.replace("_count", "s"),
            )

        return graph.render()

    def graph_poller_stats(
        self, *, start: pendulum.DateTime, end: pendulum.DateTime, title: str = ""
    ) -> bytes:
        """Graph network info."""
        rrd_file = self._network_filename()
        colors = cycle(COLORS)

        graph = Graph(
            title=title or "poller stats",
            vertical_label="time (seconds)",
            start=start,
            end=end,
        )

        for ds in ("poller_time", "total_time"):
            graph.add_summarized_ds(
                definition=f"DEF:{ds}={rrd_file}:{ds}:AVERAGE",
                v_name=ds,
                color=next(colors),
                style="LINE1",
                legend=ds.replace("_time", ""),
            )
        return graph.render()

    def graph_node_uptime(
        self,
        node: Node,
        *,
        start: pendulum.DateTime,
        end: pendulum.DateTime,
        title: str = "",
    ) -> bytes:
        """Graph node uptime."""
        rrd_file = self._node_filename(node)
        graph = Graph(
            title=title or "node uptime",
            vertical_label="uptime in days",
            lower_bound=0,
            start=start,
            end=end,
        )
        graph.add_summarized_ds(
            definition=f"DEF:uptime={rrd_file!s}:uptime:AVERAGE",
            calculation="CDEF:days=uptime,86400,/",
            v_name="days",
            color="#33cc33",
            style="AREA",
            legend="uptime",
        )
        return graph.render()

    def graph_node_load(
        self,
        node: Node,
        *,
        start: pendulum.DateTime,
        end: pendulum.DateTime,
        title: str = "",
    ) -> bytes:
        """Graph node uptime."""
        rrd_file = self._node_filename(node)
        graph = Graph(
            title=title or "load average",
            vertical_label="load",
            lower_bound=0,
            start=start,
            end=end,
        )
        graph.options.extend(("-X", "0"))
        graph.add_summarized_ds(
            definition=f"DEF:load={rrd_file!s}:load:AVERAGE",
            v_name="load",
            color="#33cc33",
            style="LINE1",
            legend="load",
        )
        return graph.render()

    def graph_node_links(
        self,
        node: Node,
        *,
        start: pendulum.DateTime,
        end: pendulum.DateTime,
        title: str = "",
    ) -> bytes:
        """Graph node links."""
        rrd_file = self._node_filename(node)
        colors = cycle(COLORS)
        graph = Graph(
            title=title or f"{node.name.lower()} links",
            vertical_label="count",
            start=start,
            end=end,
        )
        graph.add_summarized_ds(
            definition=f"DEF:total={rrd_file!s}:link_count:AVERAGE",
            v_name="total",
            color=next(colors),
            style="LINE1",
        )
        graph.add_summarized_ds(
            definition=f"DEF:radio={rrd_file!s}:radio_links:AVERAGE",
            v_name="radio",
            color=next(colors),
            style="LINE1",
        )
        graph.add_summarized_ds(
            definition=f"DEF:dtd={rrd_file!s}:dtd_links:AVERAGE",
            v_name="dtd",
            color=next(colors),
            style="LINE1",
        )
        graph.add_summarized_ds(
            definition=f"DEF:tunnel={rrd_file!s}:tunnel_links:AVERAGE",
            v_name="tunnel",
            color=next(colors),
            style="LINE1",
        )

        return graph.render()

    def graph_link_cost(
        self,
        link: Link,
        *,
        start: pendulum.DateTime,
        end: pendulum.DateTime,
        title: str = "",
    ) -> bytes:
        """Graph link routing cost."""

        rrd_file = self._link_filename(link)
        graph = Graph(
            title=title or "link cost",
            start=start,
            end=end,
            vertical_label="cost",
            lower_bound=0,
        )
        graph.add_summarized_ds(
            definition=f"DEF:cost={rrd_file!s}:olsr_cost:AVERAGE",
            v_name="cost",
            color=COLORS[1],
            style="LINE1",
            legend="route cost",
        )
        return graph.render()

    def graph_link_snr(
        self,
        link: Link,
        *,
        start: pendulum.DateTime,
        end: pendulum.DateTime,
        title: str = "",
    ) -> bytes:
        """Graph node uptime."""
        rrd_file = self._link_filename(link)
        graph = Graph(
            title=title or "signal to noise ratio",
            vertical_label="db",
            start=start,
            end=end,
        )
        graph.add_summarized_ds(
            definitions=(
                f"DEF:signal={rrd_file!s}:signal:AVERAGE",
                f"DEF:noise={rrd_file!s}:noise:AVERAGE",
            ),
            calculation="CDEF:snr=signal,noise,-",
            v_name="snr",
            color="#33cc33",
            style="LINE1",
            legend="snr",
        )
        return graph.render()

    def graph_link_quality(
        self,
        link: Link,
        *,
        start: pendulum.DateTime,
        end: pendulum.DateTime,
        title: str = "",
    ) -> bytes:
        """Graph link quality and neighbor quality."""

        rrd_file = self._link_filename(link)
        graph = Graph(
            title=title or "link quality",
            start=start,
            end=end,
            vertical_label="percent",
            lower_bound=0,
        )
        graph.add_summarized_ds(
            definition=f"DEF:quality={rrd_file!s}:quality:AVERAGE",
            calculation="CDEF:lq=quality,100,*",
            v_name="lq",
            color=COLORS[0],
            style="LINE1",
            legend="local",
        )
        graph.add_summarized_ds(
            definition=f"DEF:neighbor_quality={rrd_file!s}:neighbor_quality:AVERAGE",
            calculation="CDEF:nlq=neighbor_quality,100,*",
            v_name="nlq",
            color=COLORS[1],
            style="LINE1",
            legend="neighbor",
        )
        return graph.render()

    def update_link_stats(self, link: Link) -> bool:
        # switch to async after testing!
        rrd_file = self._link_filename(link)

        timestamp = link.last_seen.int_timestamp

        # create RRD file if it doesn't exist
        if not rrd_file.exists():
            _create_link_rrd_file(rrd_file, start=timestamp)

        values = ":".join(
            _dump(v)
            for v in [
                link.olsr_cost,
                link.signal,
                link.noise,
                link.tx_rate,
                link.rx_rate,
                link.quality,
                link.neighbor_quality,
            ]
        )
        logger.trace("Updating link stats: {} -> {}", rrd_file.name, values)
        try:
            rrdtool.update(
                str(rrd_file),
                "--template",
                "olsr_cost:signal:noise:tx_rate:rx_rate:quality:neighbor_quality",
                f"{timestamp}:{values}",
            )
        except rrdtool.OperationalError as exc:
            # TODO: detect errors due to new data points and rebuild data file?
            logger.error("RRDtool error: {}", exc)
            return False
        return True

    def update_network_stats(
        self,
        *,
        node_count: int,
        link_count: int,
        error_count: int,
        poller_time: float,
        total_time: float,
    ) -> bool:
        rrd_file = self._network_filename()

        timestamp = pendulum.now().int_timestamp

        # create RRD file if it doesn't exist
        if not rrd_file.exists():
            _create_network_rrd_file(rrd_file, start=timestamp)

        values = ":".join(
            _dump(v)
            for v in [
                node_count,
                link_count,
                error_count,
                poller_time,
                total_time,
            ]
        )

        try:
            rrdtool.update(
                str(rrd_file),
                "--template",
                "node_count:link_count:error_count:poller_time:total_time",
                f"{timestamp}:{values}",
            )
        except rrdtool.OperationalError as exc:
            # TODO: detect errors due to new data points and rebuild data file?
            logger.error("RRDtool error: {}", exc)
            return False
        return True

    def _network_filename(self) -> Path:
        return self.data_path / "network.rrd"

    def _node_filename(self, node: Node) -> Path:
        return self.data_path / f"node-{node.id}.rrd"

    def _link_filename(self, link: Link) -> Path:
        return self.data_path / f"link-{link.id.dump()}.rrd"


def _create_node_rrd_file(filename: Path, *, start: int = None) -> bool:
    """Create RRD file to track node statistics."""

    args = [
        str(filename),
        "--start",
        str(start - 10) if start else "now",
        "--step",
        "300",
        "DS:link_count:GAUGE:600:0:U",
        "DS:service_count:GAUGE:600:0:U",
        "DS:uptime:GAUGE:600:0:U",
        "DS:load:GAUGE:600:0:U",
        "DS:radio_links:GAUGE:600:0:U",
        "DS:dtd_links:GAUGE:600:0:U",
        "DS:tunnel_links:GAUGE:600:0:U",
    ]
    args.extend(ARCHIVES)
    try:
        rrdtool.create(*args)
    except rrdtool.OperationalError as exc:
        logger.error("RRDtool error: {}", exc)
        return False
    return True


def _create_link_rrd_file(filename: Path, *, start: int = None) -> bool:
    """Create RRD file to track link statistics."""

    args = [str(filename)]
    if start:
        args.extend(("--start", str(start - 10)))
    args.extend(
        [
            "--step",
            "300",
            "DS:olsr_cost:GAUGE:600:0:U",
            "DS:signal:GAUGE:600:U:0",
            "DS:noise:GAUGE:600:U:0",
            "DS:tx_rate:GAUGE:600:0:U",
            "DS:rx_rate:GAUGE:600:0:U",
            "DS:quality:GAUGE:600:0:1",
            "DS:neighbor_quality:GAUGE:600:0:1",
        ]
    )
    logger.trace("Creating link RRD file: {}", args)
    args.extend(ARCHIVES)
    try:
        rrdtool.create(*args)
    except rrdtool.OperationalError as exc:
        logger.error("RRDtool error: {}", exc)
        return False
    return True


def _create_network_rrd_file(filename: Path, *, start: int = None) -> bool:
    """Create RRD file to track network and poller statistics."""

    # There is only one network file, so keeping data longer
    # (since the space won't be multiplied).

    args = [
        str(filename),
        "--start",
        str(start - 10) if start else "now",
        "--step",
        "300",
        "DS:node_count:GAUGE:600:0:U",
        "DS:link_count:GAUGE:600:0:U",
        "DS:error_count:GAUGE:600:0:U",
        "DS:poller_time:GAUGE:600:0:U",
        "DS:total_time:GAUGE:600:0:U",
        "RRA:AVERAGE:0.5:1:144",  # 1 day, resolution 5 minutes
        "RRA:MIN:0.5:1:144",
        "RRA:MAX:0.5:1:144",
        "RRA:AVERAGE:0.5:3:672",  # 7 days, resolution 15 minutes
        "RRA:MIN:0.5:3:672",
        "RRA:MAX:0.5:3:672",
        "RRA:AVERAGE:0.5:6:1440",  # 30 days, resolution 30 minutes
        "RRA:MIN:0.5:6:1440",
        "RRA:MAX:0.5:6:1440",
        "RRA:AVERAGE:0.5:24:1080",  # 90 days, resolution 2 hours
        "RRA:MIN:0.5:24:1080",
        "RRA:MAX:0.5:24:1080",
        "RRA:AVERAGE:0.5:288:1095",  # 1095 days, resolution 1 day
        "RRA:MIN:0.5:288:1095",
        "RRA:MAX:0.5:288:1095",
    ]
    try:
        rrdtool.create(*args)
    except rrdtool.OperationalError as exc:
        logger.error("RRDtool error: {}", exc)
        return False
    return True


def _dump(value: Any) -> str:
    """Dump values for RRDtool."""

    if isinstance(value, str):
        return value
    elif value is None:
        return "U"
    else:
        return str(value)


@attr.s(auto_attribs=True)
class Graph:
    """Helper class to simplify some common stuff when creating a graph."""

    start: pendulum.DateTime
    end: Optional[pendulum.DateTime] = None
    title: str = ""
    vertical_label: str = ""
    lower_bound: Optional[float] = None
    options: List[str] = attr.Factory(list)
    data_definitions: List[str] = attr.Factory(list)
    data_calculations: List[str] = attr.Factory(list)
    variable_definitions: List[str] = attr.Factory(list)
    elements: List[str] = attr.Factory(list)

    _common_stats = {
        "lst": "LAST",
        "min": "MINIMUM",
        "avg": "AVERAGE",
        "max": "MAXIMUM",
    }

    def add_summarized_ds(
        self,
        *,
        v_name: str,
        color: str,
        style: str,
        definition: str = "",
        definitions: Optional[Iterable[str]] = None,
        calculation: str = "",
        legend: str = "",
        fmt: str = "%10.2lf",
    ):
        """Add a data source to graph and print some basic stats."""
        if legend == "":
            legend = v_name
        if definition:
            self.data_definitions.append(definition)
        if definitions:
            self.data_definitions.extend(definitions)
        if calculation:
            self.data_calculations.append(calculation)
        self.variable_definitions.extend(
            f"VDEF:{stat}_{v_name}={v_name},{func}"
            for stat, func in self._common_stats.items()
        )
        if len(self.elements) == 0:
            self.elements.append(
                # FIXME: base the columns on common stats
                r"COMMENT:{:14s}{:>12s}{:>12s}{:>12s}{:>12s}\l".format(
                    "", "Last", "Minimum", "Average", "Maximum"
                )
            )
        self.elements.append(f"{style}:{v_name}{color}:{legend:12s}")
        self.elements.extend(
            f"GPRINT:{stat}_{v_name}:{fmt}" for stat in self._common_stats.keys()
        )
        self.elements[-1] += r"\l"

    def render(self) -> bytes:
        """Draw the graph via RRDtool."""

        self.options.extend(("--start", str(self.start.int_timestamp)))
        if self.end:
            self.options.extend(("--end", str(self.end.int_timestamp)))
        if self.vertical_label:
            self.options.extend(("--vertical-label", self.vertical_label))
        if self.title:
            self.options.extend(("--title", self.title))
        if self.lower_bound is not None:
            self.options.extend(("--lower-limit", str(self.lower_bound)))
        graphv_args = (
            "-",
            *self.options,
            *self.data_definitions,
            *self.data_calculations,
            *self.variable_definitions,
            *self.elements,
        )
        logger.trace("Rendering graph: {}", graphv_args)

        # this is using the default of `fork`,
        # which supposedly has issues with multi-threading,
        # however `spawn` was *very* slow (>1s vs <200ms)
        # (hopefully we're safe since otherwise we should be threadsafe)
        parent_cnxn, child_cnxn = mp.Pipe(duplex=False)
        proc = mp.Process(target=_rrdtool_graphv, args=(child_cnxn, graphv_args))
        proc.start()
        graph_info = parent_cnxn.recv()
        proc.join()

        return graph_info["image"]


def _rrdtool_graphv(cnxn, args: List[str]):
    """Wrap graphv so it can be executed in its own process."""
    # graphv appears to have threading issues (and Waitress is threaded)
    # https://github.com/oetiker/rrdtool-1.x/issues/867
    info = rrdtool.graphv(*args)
    cnxn.send(info)
    cnxn.close()
