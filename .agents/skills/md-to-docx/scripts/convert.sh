#!/usr/bin/env bash
# md-to-docx 转换脚本
# 用法:
#   convert.sh <input.md> [output.docx]
#   convert.sh <input1.md> <input2.md> ... -o <output.docx>
#   选项: --template <tpl.docx>  --output-dir <dir>
# LaTeX 公式保持原文，不转换

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_IN_SKILL="$SKILL_DIR/assets/reference.docx"

# 默认值
OUTPUT=""
TEMPLATE=""
OUTPUT_DIR=""
INPUTS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --template)
      TEMPLATE="$2"; shift 2 ;;
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    -o)
      OUTPUT="$2"; shift 2 ;;
    -h|--help)
      echo "用法: convert.sh <input.md ...> [-o output.docx] [--template tpl.docx] [--output-dir dir]"
      echo "  多个输入文件会按顺序合并转换"
      exit 0 ;;
    *)
      INPUTS+=("$1"); shift ;;
  esac
done

if [[ ${#INPUTS[@]} -eq 0 ]]; then
  echo "错误：未指定输入文件" >&2
  echo "用法: convert.sh <input.md ...> [-o output.docx] [--template tpl.docx] [--output-dir dir]" >&2
  exit 1
fi

# 检查所有输入文件存在
for f in "${INPUTS[@]}"; do
  if [[ "$f" != /* ]]; then f="$(pwd)/$f"; fi
  if [[ ! -f "$f" ]]; then
    echo "错误：文件不存在: $f" >&2; exit 1
  fi
done

# 模板：用户指定 > skill 内 assets/ > 项目 data/
if [[ -z "$TEMPLATE" ]]; then
  if [[ -f "$TEMPLATE_IN_SKILL" ]]; then
    TEMPLATE="$TEMPLATE_IN_SKILL"
  else
    # 尝试从当前目录向上查找项目根（找 config.yaml 或 data/ 目录）
    SEARCH_DIR="$(pwd)"
    for i in $(seq 1 5); do
      if [[ -f "$SEARCH_DIR/data/研究生学位论文写作指南.docx" ]]; then
        TEMPLATE="$SEARCH_DIR/data/研究生学位论文写作指南.docx"
        break
      fi
      SEARCH_DIR="$(cd "$SEARCH_DIR/.." 2>/dev/null && pwd)" || break
    done
  fi
fi

if [[ -n "$TEMPLATE" && ! -f "$TEMPLATE" ]]; then
  echo "警告：模板文件不存在: $TEMPLATE，将使用 pandoc 默认样式" >&2
  TEMPLATE=""
fi

# 输出路径推导
if [[ -z "$OUTPUT" ]]; then
  FIRST_INPUT="${INPUTS[0]}"
  if [[ "$FIRST_INPUT" != /* ]]; then FIRST_INPUT="$(pwd)/$FIRST_INPUT"; fi
  BASENAME="$(basename "$FIRST_INPUT" .md)"

  if [[ -n "$OUTPUT_DIR" ]]; then
    OUTPUT="$OUTPUT_DIR/${BASENAME}.docx"
  else
    OUTPUT="$(dirname "$FIRST_INPUT")/${BASENAME}.docx"
  fi
fi

if [[ "$OUTPUT" != /* ]]; then
  OUTPUT="$(pwd)/$OUTPUT"
fi

mkdir -p "$(dirname "$OUTPUT")"

# 输入文件转绝对路径
ABS_INPUTS=()
for f in "${INPUTS[@]}"; do
  if [[ "$f" != /* ]]; then f="$(pwd)/$f"; fi
  ABS_INPUTS+=("$f")
done

echo "输入: ${ABS_INPUTS[*]}"
echo "输出: $OUTPUT"
[[ -n "$TEMPLATE" ]] && echo "模板: $TEMPLATE"

# 执行转换（不加数学相关选项，公式保持原文）
PANDOC_CMD=(pandoc "${ABS_INPUTS[@]}" -o "$OUTPUT" --standalone --wrap=preserve)
[[ -n "$TEMPLATE" ]] && PANDOC_CMD+=(--reference-doc="$TEMPLATE")

if "${PANDOC_CMD[@]}"; then
  # Windows/跨平台获取文件大小
  if command -v stat &>/dev/null; then
    SIZE=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null || echo "?")
  else
    SIZE=$(wc -c < "$OUTPUT" 2>/dev/null | tr -d ' ' || echo "?")
  fi
  echo "转换成功！文件大小: ${SIZE} bytes → $OUTPUT"
else
  echo "转换失败" >&2; exit 1
fi
