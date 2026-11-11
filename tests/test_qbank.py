"""scripts/qbank.py 的测试：python3 -m unittest discover -s tests"""
import contextlib
import copy
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import qbank  # noqa: E402

COLLECTION = {
    "id": "demo", "title": "示例题库", "origin": "original", "source": "自编",
    "license": "CC-BY-4.0", "maintainers": ["octocat"],
}
QUESTION = {
    "id": "q1", "grade": 7, "semester": "上", "questionType": "single_choice", "text": "1 + 1 = ?",
    "options": {"A": "1", "B": "2"}, "answer": "B", "analysis": "一加一等于二。", "knowledgePoints": ["有理数的加法"],
}


def make_bank(questions, **meta):
    base = {
        "id": "demo-junior-high-math", "title": "示例", "stage": "junior_high", "subject": "math", "grades": [7],
        "count": len(questions), "tagged": True, "source": "自编", "license": "CC-BY-4.0", "updatedAt": "2026-01-01",
    }
    base.update(meta)
    return {"format": qbank.BANK_FORMAT, "version": 1, "meta": base, "questions": questions}


class RepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        (self.root / "banks" / "demo").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.addCleanup(self._tmp.cleanup)

    def write(self, questions=None, collection=None, build=True, **meta):
        bank = make_bank(questions if questions is not None else [copy.deepcopy(QUESTION)], **meta)
        directory = self.root / "banks" / "demo"
        (directory / "collection.json").write_bytes(qbank.serialize_pretty(collection or COLLECTION))
        (directory / f"{bank['meta']['id']}.json").write_bytes(qbank.serialize_bank(bank))
        if build:
            for name, content in qbank.build_outputs(self.root).items():
                (self.root / name).write_bytes(content)

    def codes(self, level="error"):
        report = qbank.Report()
        qbank.validate_repo(self.root, report)
        return {item[1] for item in report.items if item[0] == level}

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = qbank.main(["--root", str(self.root), *argv])
        return code, out.getvalue()


class ValidateTest(RepoCase):
    def test_valid_repo_passes(self):
        self.write()
        self.assertEqual(self.codes(), set())
        self.assertEqual(self.codes("warning"), set())
        self.assertEqual(self.run_cli("validate")[0], 0)

    def question_codes(self, level="error", **changes):
        question = copy.deepcopy(QUESTION)
        for key, value in changes.items():
            if value is ...:
                question.pop(key)
            else:
                question[key] = value
        self.write([question])
        return self.codes(level)

    def test_structure_errors(self):
        self.assertIn("unknown-field", self.question_codes(knowledgePoint=["x"]))
        self.assertIn("field-type", self.question_codes(id=...))
        self.assertIn("field-empty", self.question_codes(text="  "))
        self.assertIn("enum", self.question_codes(questionType="单选题"))
        self.assertIn("enum", self.question_codes(semester="秋"))
        self.assertIn("field-type", self.question_codes(grade="7"))
        self.assertIn("field-type", self.question_codes(difficultyStars=6))
        self.assertIn("knowledge-point", self.question_codes(knowledgePoints=["a", "a"]))

    def test_content_errors(self):
        self.assertIn("answer-not-in-options", self.question_codes(answer="C"))
        self.assertIn("options", self.question_codes(options={"A": "1"}, answer="A"))
        self.assertIn("control-char", self.question_codes(analysis="$\x0crac{1}{2}$"))
        self.assertIn("control-char", self.question_codes(text="乱码�"))
        self.assertIn("active-content", self.question_codes(text="<script>alert(1)</script>"))
        self.assertIn("embedded-data", self.question_codes(text="图 data:image/png;base64,AAAA"))
        self.assertIn("figure-svg", self.question_codes(figureSvg="<svg onload=\"x()\"></svg>"))
        self.assertIn("figure-svg", self.question_codes(figureSvg="not svg"))

    def test_content_warnings(self):
        self.assertIn("answer-missing", self.question_codes("warning", answer="略"))
        self.assertIn("choice-no-options", self.question_codes("warning", options=None))
        self.assertIn("single-choice-multi-answer", self.question_codes("warning", answer="AB"))
        self.assertIn("grade-out-of-stage", self.question_codes("warning", grade=3))
        self.assertIn("latex-unbalanced", self.question_codes("warning", text="求 $x 的值"))
        self.assertIn("latex-escape", self.question_codes("warning", text="$2 \times 3$"))
        self.assertIn("pii", self.question_codes("warning", text="联系电话 13812345678"))
        self.assertIn("promo", self.question_codes("warning", analysis="关注公众号获取答案"))
        self.assertIn("external-image", self.question_codes("warning", text="如图 ![](a.png)"))
        self.assertIn("mojibake", self.question_codes("warning", text="锟斤拷"))

    def test_duplicates(self):
        other = dict(copy.deepcopy(QUESTION), id="q2")
        self.write([copy.deepcopy(QUESTION), other], count=2)
        self.assertIn("duplicate-question", self.codes("warning"))
        self.write([copy.deepcopy(QUESTION), copy.deepcopy(QUESTION)], count=2)
        self.assertIn("duplicate-id", self.codes())

    def test_meta_errors(self):
        self.write(count=2)
        self.assertIn("question-count", self.codes())
        self.write(grades=[8])
        self.assertIn("meta", self.codes())
        self.write(license="MIT")
        self.assertIn("license", self.codes())
        self.write(updatedAt="2026/01/01")
        self.assertIn("meta", self.codes())

    def test_package_id_must_match_collection_and_file(self):
        self.write(id="other-junior-high-math")
        self.assertIn("package-id", self.codes())

    def test_collection_errors(self):
        self.write(collection=dict(COLLECTION, license="CC-BY-ND-4.0"))
        self.assertIn("license", self.codes())
        self.write(collection=dict(COLLECTION, origin="third_party"))
        self.assertIn("collection", self.codes())
        self.write(collection=dict(COLLECTION, maintainers=[]))
        self.assertIn("collection", self.codes())

    def test_layout_and_generated_files(self):
        self.write()
        (self.root / "banks" / "demo" / "raw.docx").write_bytes(b"x")
        self.assertIn("layout", self.codes())
        (self.root / "banks" / "demo" / "raw.docx").unlink()
        (self.root / "index.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.codes(), {"stale-generated"})
        self.assertEqual(self.run_cli("build", "--check")[0], 1)
        self.assertEqual(self.run_cli("build")[0], 0)
        self.assertEqual(self.codes(), set())

    def test_non_canonical_file_is_fixed_by_format(self):
        self.write()
        path = self.root / "banks" / "demo" / "demo-junior-high-math.json"
        path.write_text(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2), encoding="utf-8")
        self.assertIn("not-canonical", self.codes())
        self.run_cli("format")
        self.run_cli("build")
        self.assertEqual(self.codes(), set())


class PackTest(RepoCase):
    ARGS = ["--title", "示例", "--stage", "junior_high", "--subject", "math", "--source", "自编", "--license", "CC-BY-4.0"]

    def test_pack_csv_into_collection(self):
        source = self.root / "in.csv"
        source.write_text(
            "text,questionType,A,B,answer,grade,knowledgePoints\n"
            "1 + 1 = ?,单选题,1,2,B,7,有理数的加法|有理数\n"
            "1 + 1 = ?,单选题,1,2,B,7,有理数的加法\n"
            "化简 $a+a$,填空题,,,2a,7,整式的加减\n",
            encoding="utf-8",
        )
        code, out = self.run_cli("pack", str(source), "--id", "demo-junior-high-math", "--collection", "demo", "--maintainer", "octocat", *self.ARGS)
        self.assertEqual(code, 0, out)
        bank = json.loads((self.root / "banks/demo/demo-junior-high-math.json").read_text(encoding="utf-8"))
        self.assertEqual(bank["meta"]["count"], 2)
        self.assertEqual(bank["meta"]["grades"], [7])
        first = bank["questions"][0]
        self.assertEqual(first["questionType"], "single_choice")
        self.assertEqual(first["options"], {"A": "1", "B": "2"})
        self.assertEqual(first["knowledgePoints"], ["有理数的加法", "有理数"])
        self.assertTrue(first["id"].startswith("q-"))
        index = json.loads((self.root / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["packages"][0]["file"], "banks/demo/demo-junior-high-math.json")
        self.assertEqual(self.codes(), set())

    def test_pack_standalone_file(self):
        source = self.root / "in.json"
        source.write_text(json.dumps([{"text": "写一篇作文", "questionType": "writing"}], ensure_ascii=False), encoding="utf-8")
        out_file = self.root / "out" / "my-bank.json"
        code, out = self.run_cli("pack", str(source), "--id", "my-bank", "--out", str(out_file), *self.ARGS)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.run_cli("validate", str(out_file))[0], 0)

    def test_pack_rejects_bad_rows(self):
        source = self.root / "in.jsonl"
        source.write_text('{"text": "x", "questionType": "连线题"}\n', encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.run_cli("pack", str(source), "--id", "my-bank", "--out", str(self.root / "o.json"), *self.ARGS)


class RepositoryDataTest(unittest.TestCase):
    """仓库现有数据必须通过校验，并与 JSON Schema 一致。"""

    def test_repository_has_no_errors(self):
        report = qbank.Report()
        qbank.validate_repo(ROOT, report)
        self.assertEqual([item for item in report.items if item[0] == "error"], [])

    def test_files_match_json_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("未安装 jsonschema")

        def check(schema_name, path):
            schema = json.loads((ROOT / "schema" / schema_name).read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(schema).validate(json.loads(path.read_text(encoding="utf-8")))

        check("index.schema.json", ROOT / "index.json")
        for directory in qbank.iter_collections(ROOT):
            check("collection.schema.json", directory / "collection.json")
            for path in qbank.iter_packages(directory):
                check("question-bank.schema.json", path)


if __name__ == "__main__":
    unittest.main()
