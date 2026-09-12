"""ipcalc CLI エントリポイント.

計算処理は全て `common.iptools` に委譲し、ここでは引数解析と表示(rich table / JSON)のみを行う。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Any

from rich.console import Console
from rich.table import Table

from common.iptools.calc import ipv4 as ipv4_calc
from common.iptools.calc import ipv6 as ipv6_calc
from common.iptools.calc._bits import full_mask, prefix_mask
from common.iptools.calc.auto import calc as calc_auto
from common.iptools.calc.reserved import load_ipv4_reserved, load_ipv6_reserved
from common.iptools.result import IPToolsResult

console = Console()
error_console = Console(stderr=True)

IPV6_COMMON_PREFIXES = (32, 40, 44, 48, 52, 56, 60, 64, 112, 116, 120, 124, 126, 127, 128)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ipcalc",
        description=(
            "IPv4 / IPv6 アドレス・マスクからネットワーク情報を計算します。\n"
            "  ipcalc <IPv4>/<CIDR>\n"
            "  ipcalc <IPv4>/<NetMask>\n"
            "  ipcalc <IPv6>/<CIDR>"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "ipaddr_mask",
        nargs="?",
        help="計算対象。例: 172.16.201.10/24, 172.16.201.10/255.255.255.0, 2001:db8::1/64",
    )
    parser.add_argument(
        "-i", "--reserved", action="store_true", help="Special-Purpose Address Registry (予約済みIPアドレス一覧) を表示"
    )
    parser.add_argument("-m", "--masks", action="store_true", help="CIDR / ネットマスク対応表を表示")
    parser.add_argument("--json", action="store_true", help="結果をJSON形式で出力する（他ツールとの連携向け）")
    return parser


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _render_info_table(value: Any) -> Table:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("項目")
    table.add_column("値")
    for key, v in asdict(value).items():
        table.add_row(key, "-" if v is None else str(v))
    return table


def _reserved_addr_str(entry) -> str:
    if entry.bit_length == 32:
        return f"{ipv4_calc.long2ip(entry.network_int)}/{entry.prefix_length}"
    return f"{ipv6_calc.long2ip_compressed(entry.network_int)}/{entry.prefix_length}"


def _reserved_as_dicts() -> list[dict]:
    rows = []
    for version, entries in (("IPv4", load_ipv4_reserved()), ("IPv6", load_ipv6_reserved())):
        for entry in entries:
            rows.append(
                {
                    "version": version,
                    "address": _reserved_addr_str(entry),
                    "scope": entry.scope,
                    "rfc": entry.rfc,
                }
            )
    return rows


def _render_reserved_table() -> Table:
    table = Table(show_header=True, header_style="bold cyan", title="Special-Purpose Address Registry")
    table.add_column("Version")
    table.add_column("Address")
    table.add_column("Scope")
    table.add_column("RFC")
    for version, entries in (("IPv4", load_ipv4_reserved()), ("IPv6", load_ipv6_reserved())):
        for entry in entries:
            table.add_row(version, _reserved_addr_str(entry), entry.scope, entry.rfc)
    return table


def _ipv4_mask_table() -> list[dict]:
    rows = []
    for cidr in range(0, 33):
        mask_int = prefix_mask(cidr, ipv4_calc.BIT_LENGTH)
        wildcard_int = full_mask(ipv4_calc.BIT_LENGTH) ^ mask_int
        num_addresses = 1 << (ipv4_calc.BIT_LENGTH - cidr)
        num_hosts = num_addresses if cidr >= 31 else num_addresses - 2
        rows.append(
            {
                "cidr": f"/{cidr}",
                "netmask": ipv4_calc.long2ip(mask_int),
                "wildcard_mask": ipv4_calc.long2ip(wildcard_int),
                "num_addresses": num_addresses,
                "num_hosts": num_hosts,
            }
        )
    return rows


def _ipv6_prefix_table() -> list[dict]:
    return [{"cidr": f"/{p}", "num_addresses": 1 << (128 - p)} for p in IPV6_COMMON_PREFIXES]


def _render_mask_tables() -> list[Table]:
    v4 = Table(show_header=True, header_style="bold cyan", title="IPv4 CIDR / Netmask")
    for col in ("CIDR", "Netmask", "Wildcard Mask", "Addresses", "Usable Hosts"):
        v4.add_column(col)
    for row in _ipv4_mask_table():
        v4.add_row(
            row["cidr"], row["netmask"], row["wildcard_mask"], str(row["num_addresses"]), str(row["num_hosts"])
        )

    v6 = Table(show_header=True, header_style="bold cyan", title="IPv6 主要プレフィックス長")
    v6.add_column("Prefix")
    v6.add_column("Addresses")
    for row in _ipv6_prefix_table():
        v6.add_row(row["cidr"], str(row["num_addresses"]))

    return [v4, v6]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not any([args.ipaddr_mask, args.reserved, args.masks]):
        parser.print_help()
        return 1

    if args.reserved:
        if args.json:
            _print_json(_reserved_as_dicts())
        else:
            console.print(_render_reserved_table())
        return 0

    if args.masks:
        if args.json:
            _print_json({"ipv4": _ipv4_mask_table(), "ipv6": _ipv6_prefix_table()})
        else:
            for table in _render_mask_tables():
                console.print(table)
        return 0

    result: IPToolsResult = calc_auto(args.ipaddr_mask)

    if not result.ok:
        if args.json:
            _print_json({"error": result.reason.name, "message": result.message})
        else:
            error_console.print(f"[red]エラー[{result.reason.name}]:[/red] {result.message}")
        return 1

    if args.json:
        _print_json(asdict(result.value))
    else:
        console.print(_render_info_table(result.value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
