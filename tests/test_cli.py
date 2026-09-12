import json

from ipcalc.cli import main


def test_no_args_prints_help(capsys):
    code = main([])
    assert code == 1
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


def test_ipv4_calc_json_output(capsys):
    code = main(["172.16.201.10/24", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["network"] == "172.16.201.0"
    assert data["broadcast"] == "172.16.201.255"
    assert data["num_hosts"] == 254


def test_ipv6_calc_json_output(capsys):
    code = main(["2001:db8::1/64", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["network"] == "2001:db8::"
    assert data["prefix_length"] == 64


def test_invalid_input_json_error(capsys):
    code = main(["not-an-ip", "--json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["error"] == "MISSING_PREFIX"


def test_reserved_json_contains_both_versions(capsys):
    code = main(["-i", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    versions = {row["version"] for row in data}
    assert versions == {"IPv4", "IPv6"}


def test_masks_json_covers_all_ipv4_cidr(capsys):
    code = main(["-m", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["ipv4"]) == 33
    assert "/64" in {row["cidr"] for row in data["ipv6"]}


def test_table_output_smoke(capsys):
    code = main(["10.0.0.1/8"])
    assert code == 0
    captured = capsys.readouterr()
    assert "network" in captured.out
    assert "10.0.0.0" in captured.out
