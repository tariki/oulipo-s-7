"""requirements.txt(標準入力)のパッケージの、名前・版・ライセンスと、ライセンスファイルの全文を出す。

scripts/generate-licenses.sh から使う。
"""

import re
import sys
from importlib.metadata import PackageMetadata, PackageNotFoundError, files, metadata

# License の欄が長い場合はライセンス文の全文が入っているため使わない
_MAX_LICENSE_FIELD = 60
# 全文を載せるファイル(MIT・BSD などは著作権表示とライセンス文の再掲を求めるため)
_LICENSE_FILE = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE|AUTHORS)", re.IGNORECASE)


def main() -> None:
    """パッケージ名の順に「名前 版 ライセンス」を出す。"""
    names = sorted(
        {
            match.group(1).lower()
            for line in sys.stdin
            if (match := re.match(r"^([A-Za-z0-9_.-]+)==", line.strip()))
        }
    )
    sys.stdout.write("# サーバーの実行時の依存関係(scripts/generate-licenses.sh で生成)\n")
    installed = []
    for name in names:
        try:
            info = metadata(name)
        except PackageNotFoundError:
            continue  # この環境で入らない依存関係(別のOS向けなど)
        installed.append(name)
        sys.stdout.write(f"{info['Name']} {info['Version']} {_license_of(info)}\n")
    for name in installed:
        info = metadata(name)
        for path in sorted(files(name) or [], key=str):
            if _LICENSE_FILE.match(path.name):
                sys.stdout.write(f"\n===== {info['Name']} {info['Version']}: {path.name} =====\n\n")
                sys.stdout.write(path.read_text(encoding="utf-8").rstrip() + "\n")


def _license_of(info: PackageMetadata) -> str:
    """License-Expression、短い License、分類子の順にライセンスを探す。"""
    expression = info.get("License-Expression")
    if expression:
        return expression
    license_field = info.get("License")
    if license_field and "\n" not in license_field and len(license_field) <= _MAX_LICENSE_FIELD:
        return license_field
    classifiers = info.get_all("Classifier") or []
    licenses = [c.split(" :: ")[-1] for c in classifiers if c.startswith("License ::")]
    return " / ".join(licenses) or "UNKNOWN"


if __name__ == "__main__":
    main()
