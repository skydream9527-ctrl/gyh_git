"""emoji / 乱码 / 变体符清洗工具

用途：签约清单 vs 内容池作者名匹配时做容错。

清洗规则：
- 保留：CJK、英文字母、数字、中英文括号
- 移除：所有 Symbol / Mark / Separator / Control 类 Unicode 字符（含 emoji、乱码占位符 �、变体选择符 ️、零宽字符等）
"""
import unicodedata


def strict_clean(s):
    """严格清洗作者名：仅保留字母/数字/CJK/括号。

    Examples:
        >>> strict_clean("动物世界🐅")
        '动物世界'
        >>> strict_clean("胖豆子�")
        '胖豆子'
        >>> strict_clean("🎀达子🎀")
        '达子'
    """
    if not s:
        return ''
    result = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat[0] in ('L', 'N'):          # Letter / Number
            result.append(ch)
        elif ch in '（）()':                # 保留括号
            result.append(ch)
        # 其他（S Symbol / M Mark / Z Separator / C Control）全部丢弃
    return ''.join(result)


if __name__ == '__main__':
    tests = [
        ("动物世界🐅", "动物世界"),
        ("胖豆子�", "胖豆子"),
        ("🎀达子🎀", "达子"),
        ("听风热点追踪🇨🇳", "听风热点追踪"),
        ("赵金婷台球器材 ", "赵金婷台球器材"),
        ("乔乔谈案", "乔乔谈案"),
        ("", ""),
    ]
    all_ok = True
    for inp, expected in tests:
        got = strict_clean(inp)
        if got != expected:
            print(f"FAIL: {inp!r} → {got!r} (expected {expected!r})")
            all_ok = False
    if all_ok:
        print("emoji_clean.strict_clean self-test PASSED")
