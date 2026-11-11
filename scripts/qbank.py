#!/usr/bin/env python3
"""共享题库工具：pack（打包）/ format（规范化）/ validate（校验）/ build（生成索引与目录）。

仅依赖 Python 3.9+ 标准库。格式与规则说明见 docs/FORMAT.md。
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys

BANK_FORMAT = "wrong-notebook-question-bank"
INDEX_FORMAT = "wrong-notebook-question-bank-index"
VERSION = 1

STAGES = ["primary", "junior_high", "senior_high", "university"]
STAGE_NAMES = {"primary": "小学", "junior_high": "初中", "senior_high": "高中", "university": "大学"}
STAGE_GRADES = {"primary": (1, 6), "junior_high": (7, 9), "senior_high": (10, 12)}
SUBJECTS = ["math", "english", "chinese", "science", "physics", "chemistry", "biology", "history", "geography", "politics"]
SUBJECT_NAMES = {
    "math": "数学", "english": "英语", "chinese": "语文", "science": "科学", "physics": "物理",
    "chemistry": "化学", "biology": "生物", "history": "历史", "geography": "地理", "politics": "政治",
}
QUESTION_TYPES = ["single_choice", "multiple_choice", "true_false", "fill_blank", "calculation", "solution", "reading", "cloze", "writing", "other"]
TYPE_ALIASES = {
    "单选题": "single_choice", "单选": "single_choice", "单项选择题": "single_choice", "选择题": "single_choice",
    "多选题": "multiple_choice", "多选": "multiple_choice", "多项选择题": "multiple_choice", "不定项选择题": "multiple_choice",
    "判断题": "true_false", "判断": "true_false",
    "填空题": "fill_blank", "填空": "fill_blank",
    "计算题": "calculation", "计算": "calculation",
    "解答题": "solution", "简答题": "solution", "应用题": "solution", "证明题": "solution", "综合题": "solution",
    "阅读理解": "reading", "阅读题": "reading", "阅读": "reading",
    "完形填空": "cloze",
    "写作": "writing", "作文": "writing", "书面表达": "writing",
    "其他": "other",
}
# 允许再分发并允许改编（格式转换属于改编）的许可；不在表内的先开 Issue 讨论
LICENSES = [
    "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-NC-4.0", "CC-BY-NC-SA-4.0",
    "MIT", "Apache-2.0", "BSD-3-Clause", "PDDL-1.0", "ODbL-1.0",
]
ORIGINS = ["third_party", "original"]

MAX_QUESTIONS = 5000              # 应用单包上限
MAX_FILE_BYTES = 5 * 1024 * 1024  # 单包文件上限，保证 CDN 与移动端下载
MAX_PACKAGES = 500                # 应用索引上限
MAX_FIGURE_BYTES = 200 * 1024

META_KEYS = ["id", "title", "description", "stage", "subject", "grades", "count", "tagged", "source", "sourceUrl", "license", "updatedAt"]
META_REQUIRED = ["id", "title", "stage", "subject", "grades", "count", "tagged", "source", "license", "updatedAt"]
QUESTION_KEYS = ["id", "stage", "subjectKey", "grade", "semester", "questionType", "difficultyStars", "material", "text", "options", "answer", "analysis", "knowledgePoints", "source", "figureSvg"]
COLLECTION_KEYS = ["id", "title", "description", "origin", "source", "sourceUrl", "license", "obtainedAt", "maintainers", "notes"]
COLLECTION_REQUIRED = ["id", "title", "origin", "source", "license", "maintainers"]

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_RE = re.compile(r"^https?://\S+$")
HANDLE_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")

CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]|\r(?!\n)")
# JSON 转义丢失反斜杠后的 LaTeX 残留：\times → <TAB>imes、\neq → <LF>eq
LATEX_ESCAPE_RE = re.compile(r"\t(?=imes|ext\{|heta|riangle)|\n(?=eq\b|abla\b|u\b|eg\b)")
PRIVATE_USE_RE = re.compile(r"[\ue000-\uf8ff]")
MOJIBAKE_RE = re.compile(r"锟斤拷|烫烫烫|屯屯屯|Ã[\u0080-\u00bf]|â€|ï¿½")
ACTIVE_RE = re.compile(r"<\s*(script|iframe|object|embed)\b|javascript:", re.I)
DATA_URI_RE = re.compile(r"data:[a-z]+/[a-z0-9.+-]+;base64,", re.I)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img\b", re.I)
PII_RE = re.compile(
    r"(?<![\d.])1[3-9]\d{9}(?![\d.])"
    r"|(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)"
)
PROMO_RE = re.compile(r"微信号|公众号|QQ\s*群|加群|扫码|扫一扫|二维码|淘宝|菁优网|学科网|版权所有|未经许可")
SVG_UNSAFE_RE = re.compile(r"<\s*(script|foreignObject|iframe|image|use)\b|\son[a-z]+\s*=|javascript:|(?:href|src)\s*=\s*[\"']\s*(?:https?:)?//", re.I)
PLACEHOLDER_ANSWERS = {"略", "无", "暂无", "见解析", "-", "/", "?", "？"}


# ---------- 序列化 ----------

def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def ordered(obj, keys):
    """按规范键序重排；未知键保留在末尾（交给校验报错）。"""
    if not isinstance(obj, dict):
        return obj
    out = {key: obj[key] for key in keys if key in obj}
    out.update({key: value for key, value in obj.items() if key not in out})
    return out


def serialize_bank(bank):
    """规范格式：头部、meta 各一行，每题一行，便于 PR 逐题 diff。"""
    questions = bank.get("questions") or []
    lines = [
        '{"format":%s,"version":%s,' % (dumps(bank.get("format")), dumps(bank.get("version"))),
        '"meta":%s,' % dumps(ordered(bank.get("meta"), META_KEYS)),
        '"questions":[',
        ",\n".join(dumps(ordered(question, QUESTION_KEYS)) for question in questions),
        "]}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def serialize_pretty(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


# ---------- 报告 ----------

class Report:
    def __init__(self):
        self.items = []  # (level, code, file, where, message)

    def error(self, code, file, message, where=""):
        self.items.append(("error", code, file, where, message))

    def warn(self, code, file, message, where=""):
        self.items.append(("warning", code, file, where, message))

    def count(self, level):
        return sum(1 for item in self.items if item[0] == level)

    def groups(self):
        grouped = {}
        for level, code, file, where, message in self.items:
            grouped.setdefault((level, file, code), []).append((where, message))
        return sorted(grouped.items(), key=lambda kv: (kv[0][0] != "error", kv[0][1], kv[0][2]))

    def print(self, verbose=False, quiet=False, limit=3):
        for (level, file, code), entries in self.groups():
            if quiet and level != "error":
                continue
            label = "ERROR" if level == "error" else "WARN "
            print(f"{label} [{code}] {file}：{len(entries)} 处")
            shown = entries if verbose else entries[:limit]
            for where, message in shown:
                print(f"    {where + '：' if where else ''}{message}")
            if len(entries) > len(shown):
                print(f"    … 其余 {len(entries) - len(shown)} 处用 --verbose 查看")
            if level == "error" and os.environ.get("GITHUB_ACTIONS"):
                where, message = entries[0]
                print(f"::error file={file},title={code}::{len(entries)} 处，如 {where} {message}")

    def write_summary(self, title, stats, quiet=False):
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if not path:
            return
        lines = [f"## {title}", "", stats, ""]
        groups = [g for g in self.groups() if not (quiet and g[0][0] != "error")]
        if groups:
            lines += ["| 级别 | 规则 | 文件 | 数量 | 示例 |", "|---|---|---|---:|---|"]
            for (level, file, code), entries in groups:
                where, message = entries[0]
                example = f"{where} {message}".replace("|", "\\|").replace("\n", " ")[:160]
                lines.append(f"| {'❌' if level == 'error' else '⚠️'} | `{code}` | `{file}` | {len(entries)} | {example} |")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


# ---------- 单题校验 ----------

def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def text_fields(question):
    for key in ("material", "text", "answer", "analysis", "source"):
        value = question.get(key)
        if isinstance(value, str):
            yield key, value
    options = question.get("options")
    if isinstance(options, dict):
        for key, value in options.items():
            if isinstance(value, str):
                yield f"options.{key}", value
    for point in question.get("knowledgePoints") or []:
        if isinstance(point, str):
            yield "knowledgePoints", point


def answer_letters(answer):
    compact = re.sub(r"[\s,，、;；]+", "", answer)
    return list(compact) if re.fullmatch(r"[A-Z]+", compact) else None


def content_key(question):
    parts = [question.get("material") or "", question.get("text") or "", dumps(question.get("options") or {})]
    return re.sub(r"\s+", "", "\x1f".join(parts))


def check_string(report, file, where, question, key, max_len, required=False, nullable=True):
    value = question.get(key)
    if value is None:
        if required or (key in question and not nullable):
            report.error("field-type", file, f"{key} 必填", where)
        return None
    if not isinstance(value, str):
        report.error("field-type", file, f"{key} 应为字符串", where)
        return None
    if required and not value.strip():
        report.error("field-empty", file, f"{key} 不能为空", where)
    if len(value) > max_len:
        report.error("field-too-long", file, f"{key} 长度 {len(value)} 超过 {max_len}", where)
    return value


def validate_question(report, file, question, index, meta, state):
    if not isinstance(question, dict):
        report.error("field-type", file, "题目应为对象", f"questions[{index}]")
        return
    qid = question.get("id")
    where = f"#{qid}" if isinstance(qid, str) and qid else f"questions[{index}]"
    for key in question:
        if key not in QUESTION_KEYS:
            report.error("unknown-field", file, f"未知字段 {key}", where)

    check_string(report, file, where, question, "id", 200, required=True)
    if isinstance(qid, str) and qid:
        if qid != qid.strip():
            report.error("id-format", file, "id 首尾有空白", where)
        if qid in state["ids"]:
            report.error("duplicate-id", file, "包内题目 id 重复", where)
        state["ids"].add(qid)

    text = check_string(report, file, where, question, "text", 20000, required=True)
    check_string(report, file, where, question, "material", 20000)
    answer = check_string(report, file, where, question, "answer", 20000)
    check_string(report, file, where, question, "analysis", 50000)
    check_string(report, file, where, question, "source", 200)

    stage = question.get("stage", meta.get("stage"))
    if stage not in STAGES:
        report.error("enum", file, f"stage 取值无效：{stage!r}", where)
    if question.get("subjectKey", meta.get("subject")) not in SUBJECTS:
        report.error("enum", file, f"subjectKey 取值无效：{question.get('subjectKey')!r}", where)
    qtype = question.get("questionType")
    if qtype not in QUESTION_TYPES:
        report.error("enum", file, f"questionType 取值无效：{qtype!r}", where)
    if question.get("semester") not in (None, "上", "下", "全"):
        report.error("enum", file, f"semester 只能是 上/下/全/null：{question.get('semester')!r}", where)

    grade = question.get("grade")
    if grade is not None:
        if not is_int(grade) or not 1 <= grade <= 12:
            report.error("field-type", file, f"grade 应为 1–12 的整数：{grade!r}", where)
        else:
            state["grades"].add(grade)
            low, high = STAGE_GRADES.get(stage, (1, 12))
            if not low <= grade <= high:
                report.warn("grade-out-of-stage", file, f"grade {grade} 不在 {stage} 的 {low}–{high} 范围", where)
    stars = question.get("difficultyStars")
    if stars is not None and (not is_int(stars) or not 1 <= stars <= 5):
        report.error("field-type", file, f"difficultyStars 应为 1–5 的整数：{stars!r}", where)

    points = question.get("knowledgePoints")
    if points is not None:
        if not isinstance(points, list) or len(points) > 100:
            report.error("field-type", file, "knowledgePoints 应为不超过 100 项的数组", where)
        else:
            for point in points:
                if not isinstance(point, str) or not point.strip() or len(point) > 200 or point != point.strip():
                    report.error("knowledge-point", file, f"知识点应为 1–200 字且首尾无空白的字符串：{point!r}", where)
            if len(set(map(str, points))) != len(points):
                report.error("knowledge-point", file, "知识点重复", where)
            if points:
                state["tagged"] += 1

    options = question.get("options")
    option_keys = []
    if options is not None:
        if not isinstance(options, dict):
            report.error("field-type", file, "options 应为对象或 null", where)
        else:
            option_keys = list(options)
            for key, value in options.items():
                if len(key) > 10 or not isinstance(value, str) or len(value) > 5000:
                    report.error("field-type", file, f"选项 {key} 的键应不超过 10 字、值为不超过 5000 字的字符串", where)
                elif not value.strip():
                    report.error("field-empty", file, f"选项 {key} 内容为空", where)
            if len(option_keys) == 1:
                report.error("options", file, "只有 1 个选项", where)
            if option_keys and not all(re.fullmatch(r"[A-Z]", key) for key in option_keys):
                report.warn("option-keys", file, f"选项键建议用单个大写字母：{option_keys}", where)

    if qtype in ("single_choice", "multiple_choice"):
        if not option_keys:
            report.warn("choice-no-options", file, "选择题未单列 options（选项写在题干里时应用无法按选项作答）", where)
        letters = answer_letters(answer) if isinstance(answer, str) else None
        if letters and option_keys:
            missing = [letter for letter in letters if letter not in option_keys]
            if missing:
                report.error("answer-not-in-options", file, f"答案 {answer!r} 不在选项 {option_keys} 中", where)
        if letters and qtype == "single_choice" and len(set(letters)) > 1:
            report.warn("single-choice-multi-answer", file, f"单选题答案含多个选项：{answer!r}", where)

    if not isinstance(answer, str) or answer.strip() in PLACEHOLDER_ANSWERS or not answer.strip():
        report.warn("answer-missing", file, "缺少答案", where)
    if isinstance(text, str) and 0 < len(text.strip()) < 2:
        report.warn("text-too-short", file, f"题干过短：{text!r}", where)

    for key, value in text_fields(question):
        match = CONTROL_RE.search(value)
        if match:
            report.error("control-char", file, f"{key} 含控制字符或替换字符 U+{ord(match.group()):04X}（LaTeX 反斜杠未转义时常见，如 \\frac 变成换页符）", where)
        if LATEX_ESCAPE_RE.search(value):
            report.warn("latex-escape", file, f"{key} 疑似 LaTeX 反斜杠丢失（\\times、\\neq 等被当成制表符或换行）", where)
        match = ACTIVE_RE.search(value)
        if match:
            report.error("active-content", file, f"{key} 含脚本或嵌入内容：{match.group()!r}", where)
        if DATA_URI_RE.search(value):
            report.error("embedded-data", file, f"{key} 含 base64 内嵌数据，配图请转为 figureSvg", where)
        match = MOJIBAKE_RE.search(value)
        if match:
            report.warn("mojibake", file, f"{key} 疑似乱码：{match.group()!r}", where)
        if PRIVATE_USE_RE.search(value):
            report.warn("private-use-char", file, f"{key} 含私用区字符（常见于 Word/PDF 公式字体，显示为方块）", where)
        if IMAGE_RE.search(value):
            report.warn("external-image", file, f"{key} 引用了图片，题库包不携带图片文件", where)
        match = PII_RE.search(value)
        if match:
            report.warn("pii", file, f"{key} 疑似手机号或身份证号：{match.group()[:4]}…", where)
        match = PROMO_RE.search(value)
        if match:
            report.warn("promo", file, f"{key} 疑似水印、广告或版权声明：{match.group()!r}", where)
        if key in ("text", "material", "answer", "analysis") and len(re.findall(r"(?<!\\)\$", value)) % 2:
            report.warn("latex-unbalanced", file, f"{key} 中 $ 数量为奇数，公式可能未闭合", where)

    figure = question.get("figureSvg")
    if figure is not None:
        if not isinstance(figure, str) or "<svg" not in figure[:500]:
            report.error("figure-svg", file, "figureSvg 应为 <svg> 文本", where)
        else:
            match = SVG_UNSAFE_RE.search(figure)
            if match:
                report.error("figure-svg", file, f"figureSvg 含脚本、事件或外部引用：{match.group().strip()!r}", where)
            if len(figure.encode("utf-8")) > MAX_FIGURE_BYTES:
                report.error("figure-svg", file, f"figureSvg 超过 {MAX_FIGURE_BYTES // 1024} KB", where)

    if isinstance(text, str):
        key = content_key(question)
        first = state["contents"].setdefault(key, where)
        if first != where:
            report.warn("duplicate-question", file, f"与 {first} 内容相同", where)


# ---------- 包与来源集校验 ----------

def validate_meta(report, file, meta, path, collection):
    for key in meta:
        if key not in META_KEYS:
            report.error("unknown-field", file, f"meta 未知字段 {key}")
    for key in META_REQUIRED:
        if key not in meta:
            report.error("meta", file, f"meta 缺少 {key}")
    pid = meta.get("id")
    if not isinstance(pid, str) or not SLUG_RE.match(pid) or len(pid) > 100:
        report.error("package-id", file, f"meta.id 只能用小写字母、数字和连字符：{pid!r}")
    elif path.stem != pid and path.parent.parent.name == "banks":
        report.error("package-id", file, f"文件名应为 {pid}.json")
    for key, max_len in (("title", 200), ("description", 1000), ("source", 200), ("license", 200)):
        value = meta.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > max_len):
            report.error("meta", file, f"meta.{key} 应为 1–{max_len} 字的字符串")
    if meta.get("stage") not in STAGES:
        report.error("enum", file, f"meta.stage 取值无效：{meta.get('stage')!r}")
    if meta.get("subject") not in SUBJECTS:
        report.error("enum", file, f"meta.subject 取值无效：{meta.get('subject')!r}")
    grades = meta.get("grades")
    if not isinstance(grades, list) or not all(is_int(g) and 1 <= g <= 12 for g in grades) or grades != sorted(set(grades)):
        report.error("meta", file, "meta.grades 应为升序、不重复的 1–12 整数数组")
    if not isinstance(meta.get("tagged"), bool):
        report.error("meta", file, "meta.tagged 应为布尔值")
    if "sourceUrl" in meta and not (isinstance(meta["sourceUrl"], str) and URL_RE.match(meta["sourceUrl"]) and len(meta["sourceUrl"]) <= 500):
        report.error("meta", file, "meta.sourceUrl 应为 http(s) 链接")
    if not (isinstance(meta.get("updatedAt"), str) and DATE_RE.match(meta["updatedAt"])):
        report.error("meta", file, "meta.updatedAt 应为 YYYY-MM-DD")
    if collection:
        cid = collection.get("id")
        if isinstance(pid, str) and isinstance(cid, str) and not pid.startswith(cid + "-"):
            report.error("package-id", file, f"meta.id 应以来源集 id 开头：{cid}-…")
        if meta.get("license") != collection.get("license"):
            report.error("license", file, f"meta.license 应与 collection.json 一致：{collection.get('license')!r}")


def validate_bank(report, path, file, collection=None):
    """校验单个题库包；结构可读时返回 (meta, raw)，否则返回 None。"""
    raw = path.read_bytes()
    if len(raw) > MAX_FILE_BYTES:
        report.error("file-too-large", file, f"文件 {len(raw)} 字节，超过 {MAX_FILE_BYTES} 字节上限，请拆包")
    if raw.startswith(b"\xef\xbb\xbf"):
        report.error("encoding", file, "文件带 BOM，请存为无 BOM 的 UTF-8")
        return None
    try:
        bank = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        report.error("json", file, f"不是合法的 UTF-8 JSON：{exc}")
        return None
    if not isinstance(bank, dict) or bank.get("format") != BANK_FORMAT or bank.get("version") != VERSION:
        report.error("format", file, f"format/version 应为 {BANK_FORMAT} v{VERSION}")
        return None
    meta, questions = bank.get("meta"), bank.get("questions")
    if not isinstance(meta, dict) or not isinstance(questions, list):
        report.error("format", file, "meta 应为对象，questions 应为数组")
        return None
    for key in bank:
        if key not in ("format", "version", "meta", "questions"):
            report.error("unknown-field", file, f"顶层未知字段 {key}")

    before = report.count("error")
    validate_meta(report, file, meta, path, collection)
    if not 1 <= len(questions) <= MAX_QUESTIONS:
        report.error("question-count", file, f"题数 {len(questions)} 应在 1–{MAX_QUESTIONS} 之间，超出请拆包")
    if meta.get("count") != len(questions):
        report.error("question-count", file, f"meta.count={meta.get('count')!r} 与实际题数 {len(questions)} 不一致")

    state = {"ids": set(), "contents": {}, "grades": set(), "tagged": 0}
    for index, question in enumerate(questions):
        validate_question(report, file, question, index, meta, state)

    if meta.get("tagged") is True and state["tagged"] == 0:
        report.error("meta", file, "meta.tagged 为 true，但没有题目带知识点")
    if meta.get("tagged") is False and questions and state["tagged"] == len(questions):
        report.warn("meta-tagged", file, "所有题目都带知识点，meta.tagged 可设为 true")
    if isinstance(meta.get("grades"), list) and not state["grades"] <= set(g for g in meta["grades"] if is_int(g)):
        report.error("meta", file, f"meta.grades 未覆盖题目中出现的年级 {sorted(state['grades'])}")
    if report.count("error") == before and raw != serialize_bank(bank):
        report.error("not-canonical", file, "文件不是规范格式，运行 python3 scripts/qbank.py format 修复")
    return meta, raw


def validate_collection(report, directory, file):
    path = directory / "collection.json"
    if not path.is_file():
        report.error("collection", file, "缺少 collection.json")
        return None
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        report.error("json", file, f"不是合法的 UTF-8 JSON：{exc}")
        return None
    if not isinstance(data, dict):
        report.error("collection", file, "应为 JSON 对象")
        return None
    for key in data:
        if key not in COLLECTION_KEYS:
            report.error("unknown-field", file, f"未知字段 {key}")
    for key in COLLECTION_REQUIRED:
        if key not in data:
            report.error("collection", file, f"缺少 {key}")
    cid = data.get("id")
    if not isinstance(cid, str) or not SLUG_RE.match(cid) or len(cid) > 40:
        report.error("collection", file, f"id 只能用小写字母、数字和连字符：{cid!r}")
    elif cid != directory.name:
        report.error("collection", file, f"id 应与目录名 {directory.name} 一致")
    for key, max_len in (("title", 200), ("description", 1000), ("source", 200), ("notes", 5000)):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > max_len):
            report.error("collection", file, f"{key} 应为 1–{max_len} 字的字符串")
    if data.get("license") not in LICENSES:
        report.error("license", file, f"license 应为 {'、'.join(LICENSES)} 之一；其他许可请先开 Issue：{data.get('license')!r}")
    origin = data.get("origin")
    if origin not in ORIGINS:
        report.error("collection", file, f"origin 应为 {' / '.join(ORIGINS)}")
    url = data.get("sourceUrl")
    if url is None and origin == "third_party":
        report.error("collection", file, "第三方来源必须填写 sourceUrl")
    if url is not None and not (isinstance(url, str) and URL_RE.match(url)):
        report.error("collection", file, "sourceUrl 应为 http(s) 链接")
    if "obtainedAt" in data and not (isinstance(data["obtainedAt"], str) and DATE_RE.match(data["obtainedAt"])):
        report.error("collection", file, "obtainedAt 应为 YYYY-MM-DD")
    maintainers = data.get("maintainers")
    if not isinstance(maintainers, list) or not maintainers or not all(isinstance(m, str) and HANDLE_RE.match(m) for m in maintainers):
        report.error("collection", file, "maintainers 应为至少一个 GitHub 用户名（不带 @）")
    if raw != serialize_pretty(ordered(data, COLLECTION_KEYS)):
        report.error("not-canonical", file, "文件不是规范格式，运行 python3 scripts/qbank.py format 修复")
    return data


# ---------- 仓库扫描、索引与目录 ----------

def iter_collections(root):
    banks = root / "banks"
    if not banks.is_dir():
        return
    for directory in sorted(banks.iterdir()):
        if directory.is_dir() and not directory.name.startswith("."):
            yield directory


def iter_packages(directory):
    for path in sorted(directory.glob("*.json")):
        if path.name != "collection.json":
            yield path


def build_outputs(root):
    """返回 {相对路径: bytes}：index.json 与 docs/CATALOG.md。"""
    packages, collections = [], []
    for directory in iter_collections(root):
        collection = json.loads((directory / "collection.json").read_text(encoding="utf-8"))
        collections.append(collection)
        for path in iter_packages(directory):
            raw = path.read_bytes()
            meta = json.loads(raw.decode("utf-8"))["meta"]
            entry = {key: meta[key] for key in ("id", "title", "description") if key in meta}
            entry["collection"] = collection["id"]
            entry.update({key: meta[key] for key in META_KEYS[3:] if key in meta})
            entry.update({
                "file": path.relative_to(root).as_posix(),
                "sizeBytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
            packages.append(entry)
    packages.sort(key=lambda p: (STAGES.index(p["stage"]), SUBJECTS.index(p["subject"]), p["id"]))
    index = {
        "format": INDEX_FORMAT,
        "version": VERSION,
        "updatedAt": max((p["updatedAt"] for p in packages), default=""),
        "packages": packages,
    }

    total = sum(p["count"] for p in packages)
    lines = [
        "# 题库目录",
        "",
        "> 本文件由 `python3 scripts/qbank.py build` 生成，请勿手工修改。",
        "",
        f"共 {len(collections)} 个来源集、{len(packages)} 个题库包、{total} 道题。",
        "",
        "## 来源集",
        "",
        "| 来源集 | 名称 | 来源 | 许可 | 包数 | 题数 | 维护者 |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for collection in collections:
        own = [p for p in packages if p["collection"] == collection["id"]]
        source = f"[{collection['source']}]({collection['sourceUrl']})" if collection.get("sourceUrl") else collection["source"]
        maintainers = " ".join(f"[@{m}](https://github.com/{m})" for m in collection["maintainers"])
        lines.append(
            f"| [`{collection['id']}`](../banks/{collection['id']}/collection.json) | {collection['title']} | {source} "
            f"| {collection['license']} | {len(own)} | {sum(p['count'] for p in own)} | {maintainers} |"
        )
    for stage in STAGES:
        own = [p for p in packages if p["stage"] == stage]
        if not own:
            continue
        lines += [
            "",
            f"## {STAGE_NAMES[stage]}（{sum(p['count'] for p in own)} 题）",
            "",
            "| 学科 | 题库包 | 名称 | 题数 | 年级 | 知识点 | 许可 | 大小 |",
            "|---|---|---|---:|---|---|---|---:|",
        ]
        for p in own:
            grades = p["grades"]
            grade_text = "—" if not grades else (str(grades[0]) if len(grades) == 1 else f"{grades[0]}–{grades[-1]}")
            lines.append(
                f"| {SUBJECT_NAMES[p['subject']]} | [`{p['id']}`](../{p['file']}) | {p['title']} | {p['count']} "
                f"| {grade_text} | {'有' if p['tagged'] else '无'} | {p['license']} | {p['sizeBytes'] / 1024:.0f} KB |"
            )
    return {
        "index.json": serialize_pretty(index),
        "docs/CATALOG.md": ("\n".join(lines) + "\n").encode("utf-8"),
    }


def validate_repo(root, report):
    banks = root / "banks"
    seen, package_count, question_count = {}, 0, 0
    for child in sorted(banks.iterdir()) if banks.is_dir() else []:
        if child.name == ".DS_Store":
            continue
        rel = child.relative_to(root).as_posix()
        if not child.is_dir():
            report.error("layout", rel, "banks/ 下只能放来源集目录")
            continue
        collection = validate_collection(report, child, f"{rel}/collection.json")
        packages = 0
        for path in sorted(child.iterdir()):
            file = path.relative_to(root).as_posix()
            if path.name in ("collection.json", ".DS_Store"):
                continue
            if path.is_dir() or path.suffix != ".json":
                report.error("layout", file, "来源集目录下只能放 collection.json 和题库包 .json")
                continue
            packages += 1
            result = validate_bank(report, path, file, collection)
            if result:
                meta = result[0]
                package_count += 1
                question_count += len(json.loads(result[1])["questions"])
                if meta.get("id") in seen:
                    report.error("package-id", file, f"包 id 与 {seen[meta.get('id')]} 重复")
                seen.setdefault(meta.get("id"), file)
        if packages == 0:
            report.error("layout", rel, "来源集目录下没有题库包")
    if package_count > MAX_PACKAGES:
        report.error("layout", "index.json", f"题库包数 {package_count} 超过应用索引上限 {MAX_PACKAGES}")
    if report.count("error") == 0:
        for name, content in build_outputs(root).items():
            target = root / name
            if not target.is_file() or target.read_bytes() != content:
                report.error("stale-generated", name, "与题库内容不一致，运行 python3 scripts/qbank.py build 重新生成")
    return package_count, question_count


# ---------- 打包 ----------

def load_rows(path):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with open(path, encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    text = path.read_text(encoding="utf-8-sig")
    if suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("questions")
    if not isinstance(data, list):
        raise SystemExit("输入 JSON 应为题目数组，或含 questions 数组的对象")
    return data


def normalize_row(row, number, problems):
    """把一行输入整理成题目对象；无法修复的问题记入 problems。"""
    question = {}
    options = {}
    for key, value in row.items():
        if key is None:
            continue
        key = key.strip()
        if isinstance(value, str):
            value = value.strip()
        if value is None or value == "" or value == [] or value == {}:
            continue
        option = re.fullmatch(r"(?:option[_ ]?|选项)?([A-H])", key, re.I)
        if option and key not in QUESTION_KEYS:
            options[option.group(1).upper()] = str(value)
        else:
            question[key] = value
    if isinstance(question.get("options"), str):
        try:
            question["options"] = json.loads(question["options"])
        except ValueError:
            problems.append(f"第 {number} 行：options 不是合法 JSON")
    if options and "options" not in question:
        question["options"] = options
    if isinstance(question.get("knowledgePoints"), str):
        question["knowledgePoints"] = [p.strip() for p in re.split(r"[|;；\n]", question["knowledgePoints"]) if p.strip()]
    if isinstance(question.get("knowledgePoints"), list):
        question["knowledgePoints"] = list(dict.fromkeys(p.strip() for p in question["knowledgePoints"] if isinstance(p, str) and p.strip()))
    for key in ("grade", "difficultyStars"):
        if isinstance(question.get(key), str) and re.fullmatch(r"\d+", question[key]):
            question[key] = int(question[key])
    for key in ("id", "answer"):
        if is_int(question.get(key)) or isinstance(question.get(key), float):
            question[key] = str(question[key])
    qtype = question.get("questionType")
    if isinstance(qtype, str):
        question["questionType"] = TYPE_ALIASES.get(qtype, qtype.lower().replace(" ", "_").replace("-", "_"))
    if question.get("questionType") not in QUESTION_TYPES:
        problems.append(f"第 {number} 行：questionType 无法识别（{qtype!r}），可用取值见 docs/FORMAT.md")
    if not isinstance(question.get("text"), str):
        problems.append(f"第 {number} 行：缺少 text")
    return question


def cmd_pack(args):
    root = pathlib.Path(args.root).resolve()
    if bool(args.collection) == bool(args.out):
        raise SystemExit("--collection（写入本仓库）与 --out（只导出一个文件）二选一")
    if not SLUG_RE.match(args.id):
        raise SystemExit("--id 只能用小写字母、数字和连字符")
    problems, questions, seen_content, dropped = [], [], set(), 0
    used_ids = set()
    for number, row in enumerate(load_rows(pathlib.Path(args.input)), start=1):
        if not isinstance(row, dict):
            problems.append(f"第 {number} 行：不是对象")
            continue
        question = normalize_row(row, number, problems)
        key = content_key(question)
        if key in seen_content:
            dropped += 1
            continue
        seen_content.add(key)
        if "id" not in question:
            question["id"] = "q-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
        if question["id"] in used_ids:
            problems.append(f"第 {number} 行：id {question['id']!r} 重复")
        used_ids.add(question["id"])
        questions.append(question)
    if problems:
        print("\n".join(problems[:50]), file=sys.stderr)
        raise SystemExit(f"共 {len(problems)} 个问题，修正输入后重试")
    if not questions:
        raise SystemExit("输入中没有题目")

    if args.collection:
        directory = root / "banks" / args.collection
        if not args.id.startswith(args.collection + "-"):
            raise SystemExit(f"--id 应以来源集 id 开头：{args.collection}-…")
        collection_path = directory / "collection.json"
        if not collection_path.exists():
            if not args.maintainer:
                raise SystemExit("新来源集需要 --maintainer <GitHub 用户名>")
            directory.mkdir(parents=True, exist_ok=True)
            collection = {
                "id": args.collection, "title": args.collection_title or args.title,
                "origin": args.origin or ("third_party" if args.source_url else "original"),
                "source": args.source, "sourceUrl": args.source_url, "license": args.license,
                "obtainedAt": args.updated_at, "maintainers": args.maintainer, "notes": args.notes,
            }
            collection_path.write_bytes(serialize_pretty({k: v for k, v in collection.items() if v}))
            print(f"已创建 {collection_path.relative_to(root)}，请补全说明")
    else:
        directory = None

    chunks = [questions[i:i + MAX_QUESTIONS] for i in range(0, len(questions), MAX_QUESTIONS)]
    written = []
    for number, chunk in enumerate(chunks, start=1):
        suffix = f"-p{number}" if len(chunks) > 1 else ""
        title = f"{args.title}（{number}/{len(chunks)}）" if len(chunks) > 1 else args.title
        grades = sorted({q["grade"] for q in chunk if is_int(q.get("grade"))})
        meta = {
            "id": args.id + suffix, "title": title, "description": args.description,
            "stage": args.stage, "subject": args.subject, "grades": grades, "count": len(chunk),
            "tagged": any(q.get("knowledgePoints") for q in chunk),
            "source": args.source, "sourceUrl": args.source_url, "license": args.license, "updatedAt": args.updated_at,
        }
        meta = {k: v for k, v in meta.items() if v is not None}
        bank = {"format": BANK_FORMAT, "version": VERSION, "meta": meta, "questions": chunk}
        if directory:
            target = directory / f"{meta['id']}.json"
        else:
            out = pathlib.Path(args.out)
            target = out.with_name(f"{meta['id']}.json") if len(chunks) > 1 or out.is_dir() else out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(serialize_bank(bank))
        written.append(target)
        print(f"已写入 {target}（{len(chunk)} 题）")
    if dropped:
        print(f"已去除 {dropped} 道内容完全相同的题目")
    if directory:
        for name, content in build_outputs(root).items():
            (root / name).write_bytes(content)
        print("已更新 index.json 与 docs/CATALOG.md")
        return run_validate(root, [], args)
    return run_validate(root, [str(p) for p in written], args)


# ---------- 命令 ----------

def run_validate(root, paths, args):
    report = Report()
    if paths:
        packages = questions = 0
        for name in paths:
            path = pathlib.Path(name).resolve()
            directory = path.parent
            collection = None
            if (directory / "collection.json").is_file():
                collection = validate_collection(report, directory, str(directory / "collection.json"))
            result = validate_bank(report, path, name, collection)
            if result:
                packages += 1
                questions += len(json.loads(result[1])["questions"])
    else:
        packages, questions = validate_repo(root, report)
    quiet = getattr(args, "quiet", False)
    report.print(verbose=getattr(args, "verbose", False), quiet=quiet)
    errors, warnings = report.count("error"), report.count("warning")
    stats = f"{packages} 个题库包、{questions} 道题；{errors} 个错误、{warnings} 个警告"
    report.write_summary("题库校验（指定的题库包）" if paths else "题库校验（全仓库）", stats, quiet=quiet)
    failed = errors or (getattr(args, "strict", False) and warnings)
    print(f"{'FAIL' if failed else 'OK'}：{stats}", file=sys.stderr if failed else sys.stdout)
    return 1 if failed else 0


def cmd_validate(args):
    return run_validate(pathlib.Path(args.root).resolve(), args.paths, args)


def cmd_format(args):
    root = pathlib.Path(args.root).resolve()
    if args.paths:
        targets = [pathlib.Path(p).resolve() for p in args.paths]
    else:
        targets = [p for d in iter_collections(root) for p in sorted(d.glob("*.json"))]
    changed = 0
    for path in targets:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"))
        if path.name == "collection.json":
            content = serialize_pretty(ordered(data, COLLECTION_KEYS))
        else:
            if isinstance(data.get("meta"), dict) and isinstance(data.get("questions"), list):
                data["meta"]["count"] = len(data["questions"])
            content = serialize_bank(data)
        if content != raw:
            path.write_bytes(content)
            changed += 1
            print(f"已规范化 {path}")
    print(f"共 {len(targets)} 个文件，改写 {changed} 个")
    return 0


def cmd_build(args):
    root = pathlib.Path(args.root).resolve()
    stale = []
    for name, content in build_outputs(root).items():
        target = root / name
        if target.is_file() and target.read_bytes() == content:
            continue
        stale.append(name)
        if not args.check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    if args.check and stale:
        print(f"FAIL：{'、'.join(stale)} 未更新，运行 python3 scripts/qbank.py build", file=sys.stderr)
        return 1
    print("生成文件已是最新" if not stale else f"已更新 {'、'.join(stale)}")
    return 0


def main(argv=None):
    default_root = str(pathlib.Path(__file__).resolve().parent.parent)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=default_root, help="仓库根目录，默认为本脚本所在仓库")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="校验整个仓库，或只校验指定的题库包文件")
    p.add_argument("paths", nargs="*", help="题库包文件；省略时校验整个仓库（含索引是否最新）")
    p.add_argument("--strict", action="store_true", help="有警告也返回失败")
    p.add_argument("--verbose", action="store_true", help="列出全部问题")
    p.add_argument("--quiet", action="store_true", help="只列出错误，警告只计数")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("format", help="把题库包与 collection.json 改写为规范格式")
    p.add_argument("paths", nargs="*", help="省略时处理 banks/ 下全部文件")
    p.set_defaults(func=cmd_format)

    p = sub.add_parser("build", help="生成 index.json 与 docs/CATALOG.md")
    p.add_argument("--check", action="store_true", help="只检查是否最新，不写文件")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("pack", help="把 JSON / JSONL / CSV 题目打包为题库包")
    p.add_argument("input", help="题目文件：.json（数组）、.jsonl 或 .csv")
    p.add_argument("--id", required=True, help="包 id，如 myschool-junior-high-math")
    p.add_argument("--title", required=True)
    p.add_argument("--stage", required=True, choices=STAGES)
    p.add_argument("--subject", required=True, choices=SUBJECTS)
    p.add_argument("--source", required=True, help="来源名称")
    p.add_argument("--license", required=True, help="许可；共享到本仓库时须为：" + " / ".join(LICENSES))
    p.add_argument("--source-url")
    p.add_argument("--description")
    p.add_argument("--updated-at", default=datetime.date.today().isoformat())
    p.add_argument("--collection", help="来源集 id；写入 banks/<来源集>/ 并更新索引")
    p.add_argument("--out", help="只导出文件到该路径（不共享时使用）")
    p.add_argument("--collection-title", help="新建来源集时的名称，默认同 --title")
    p.add_argument("--origin", choices=ORIGINS, help="新建来源集时的来源性质")
    p.add_argument("--maintainer", action="append", help="新建来源集时的维护者 GitHub 用户名，可重复")
    p.add_argument("--notes", help="新建来源集时的转换说明")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=cmd_pack)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
