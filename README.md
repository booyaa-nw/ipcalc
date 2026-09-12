# ipcalc

IPv4 / IPv6 のアドレス・マスクからネットワーク情報を計算するCLIツール。

計算処理は `tools/common`（`common.iptools`）に委譲しており、本ツールは引数解析・表示
（rich table / JSON）のみを担うフロントエンドです。

## Usage

### IPアドレス計算

```powershell
ipcalc <IPv4>/<CIDR>
ipcalc <IPv4>/<NetMask>
ipcalc <IPv6>/<CIDR>
```

例:

```powershell
ipcalc 172.16.201.10/24
ipcalc 172.16.201.10/255.255.255.0
ipcalc 2001:db8::1/64
```

### Special-Purpose Address Registry（予約済みIPアドレス一覧）

```powershell
ipcalc -i
ipcalc --reserved
```

### CIDR / ネットマスク対応表

```powershell
ipcalc -m
ipcalc --masks
```

### JSON出力

```powershell
ipcalc 172.16.201.10/24 --json
ipcalc -i --json
ipcalc -m --json
```

エラー時もJSONで返る（他ツール連携用）:

```json
{
  "error": "INVALID_ADDRESS",
  "message": "不正なIPv4アドレスです: '999.1.1.1'"
}
```

## 開発

```powershell
cd tools/ipcalc
uv run pytest
```
