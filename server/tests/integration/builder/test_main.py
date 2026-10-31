import json
from pathlib import Path

import pytest
from fixtures.fake_tokenizer import FakeTokenizer
from fixtures.sample_wordnet import SAMPLE_EXCLUDED, SAMPLE_READINGS, create_sample_wordnet

from s7.adapters.tokenizer import Tokenizer
from s7builder.__main__ import REPO_ROOT, main


def _fake_tokenizer() -> Tokenizer:
    return FakeTokenizer(SAMPLE_READINGS)


def _args(tmp_path: Path, **overrides: Path) -> list[str]:
    paths = {
        "wordnet": tmp_path / "wnjpn.db",
        "excluded": tmp_path / "excluded-lemmas.txt",
        "license": tmp_path / "wordnet-ja.txt",
        "output": tmp_path / "build" / "s7dict.sqlite",
        "report": tmp_path / "reports" / "build-report.json",
    } | overrides
    return ["build", *(arg for name, path in paths.items() for arg in (f"--{name}", str(path)))]


@pytest.fixture
def prepared(tmp_path: Path) -> Path:
    create_sample_wordnet(tmp_path / "wnjpn.db")
    (tmp_path / "excluded-lemmas.txt").write_text(SAMPLE_EXCLUDED, encoding="utf-8")
    (tmp_path / "wordnet-ja.txt").write_text("license", encoding="utf-8")
    return tmp_path


def test_main_build_writes_dictionary_and_report(prepared: Path) -> None:
    # When
    code = main(_args(prepared), tokenizer_factory=_fake_tokenizer)

    # Then
    assert code == 0
    assert (prepared / "build" / "s7dict.sqlite").is_file()
    report = json.loads((prepared / "reports" / "build-report.json").read_text(encoding="utf-8"))
    assert report["meta"]["lemma_count"] == 11
    assert report["meta"]["sudachidict_version"].startswith("core-")
    assert report["excluded_lemma_count"] == 1


def test_main_build_report_is_stable(prepared: Path) -> None:
    """報告に毎回変わる値を入れない(作り直した報告をコミット済みのものと比べられるように)。"""
    report = prepared / "reports" / "build-report.json"
    main(_args(prepared), tokenizer_factory=_fake_tokenizer)
    first = report.read_bytes()

    main(_args(prepared), tokenizer_factory=_fake_tokenizer)

    assert report.read_bytes() == first
    assert first.endswith(b"}\n")


def test_main_without_excluded_list_exits_with_1(
    prepared: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given
    (prepared / "excluded-lemmas.txt").unlink()

    # When
    code = main(_args(prepared), tokenizer_factory=_fake_tokenizer)

    # Then
    assert code == 1
    assert "置換先から除外する語のリストがありません" in capsys.readouterr().err
    assert not (prepared / "build" / "s7dict.sqlite").exists()


def test_main_without_license_exits_with_1(
    prepared: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (prepared / "wordnet-ja.txt").unlink()

    code = main(_args(prepared), tokenizer_factory=_fake_tokenizer)

    assert code == 1
    assert "ライセンス文がありません" in capsys.readouterr().err


def test_main_resolves_default_paths_from_repo_root(
    prepared: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """パスを省くとリポジトリ直下を基準にする(どのディレクトリから実行しても同じ)。"""
    # Given: 出力先だけを一時ディレクトリにする
    monkeypatch.chdir(prepared)
    captured: dict[str, Path] = {}

    def fake_build(self: object, wordnet: Path, excluded: Path, output: Path) -> None:
        captured.update(wordnet=wordnet, excluded=excluded)
        raise SystemExit(0)

    monkeypatch.setattr("s7builder.dictionary_builder.DictionaryBuilder.build", fake_build)

    # When
    with pytest.raises(SystemExit):
        main(["build", "--output", str(prepared / "out.sqlite")], tokenizer_factory=_fake_tokenizer)

    # Then
    assert captured == {
        "wordnet": REPO_ROOT / "data" / "source" / "wnjpn.db",
        "excluded": REPO_ROOT / "data" / "excluded-lemmas.txt",
    }


def test_main_with_broken_wordnet_exits_with_1(
    prepared: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: テーブルの無い空のSQLite
    (prepared / "wnjpn.db").unlink()
    (prepared / "wnjpn.db").touch()

    # When
    code = main(_args(prepared), tokenizer_factory=_fake_tokenizer)

    # Then: トレースバックではなく理由の1行
    assert code == 1
    assert "日本語WordNetとして読めません" in capsys.readouterr().err


def test_main_with_unwritable_output_exits_with_1(
    prepared: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: 出力先のディレクトリの場所にファイルがある
    (prepared / "build").write_text("", encoding="utf-8")

    # When
    code = main(_args(prepared), tokenizer_factory=_fake_tokenizer)

    # Then
    assert code == 1
    assert "辞書のビルドに失敗しました" in capsys.readouterr().err
