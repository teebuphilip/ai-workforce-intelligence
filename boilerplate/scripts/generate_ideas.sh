#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# FOUNDEROPS IDEA GENERATOR
#
# Generates startup ideas ONLY - no Block A/B passes.
# Fast and cheap. Use to build a pool of ideas, then run
# run_intake.sh on the ones you select.
#
# USAGE:
#   ./generate_ideas.sh [num_ideas] [idea_directive]
#
# EXAMPLES:
#   ./generate_ideas.sh           # 25 ideas, default directive
#   ./generate_ideas.sh 50        # 50 ideas
#   ./generate_ideas.sh 100 ./my_idea_directive.txt
#
# OUTPUT:
#   ideas/{startup_id}.txt  ← one file per idea, one-liner description
#
# COST:
#   ~$0.003 per idea (~$0.08 for 25 ideas)
#
# REQUIRES:
#   - ANTHROPIC_API_KEY env var
#   - curl, jq
#   - idea_generation_directive.txt (or pass path as arg2)
# ============================================================

NUM_IDEAS="${1:-25}"
IDEA_DIRECTIVE="${2:-./idea_generation_directive.txt}"

# ---- CONFIG ------------------------------------------------

OUTPUT_DIR="ideas"
FAIL_DIR="failures"

MODEL="claude-sonnet-4-5-20250929"
API_URL="https://api.anthropic.com/v1/messages"

# Creative temperature - vary ideas
TEMPERATURE=1
MAX_TOKENS=500

SLEEP_BETWEEN=2   # seconds between calls (rate limit buffer)

# ---- VALIDATION --------------------------------------------

: "${ANTHROPIC_API_KEY:?ERROR: ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY='sk-ant-...'}"

[[ -f "$IDEA_DIRECTIVE" ]] || {
    echo "ERROR: Idea directive not found: $IDEA_DIRECTIVE"
    echo ""
    echo "Create idea_generation_directive.txt with content like:"
    echo "  Generate a creative startup idea."
    echo "  Output format:"
    echo "    STARTUP_IDEA_ID: {slug_lowercase}"
    echo "    DESCRIPTION: {one sentence describing the business}"
    echo ""
    echo "  Rules:"
    echo "    - Different each time"
    echo "    - Real problem, real market"
    echo "    - No calculators or simple utilities"
    echo "    - No AI buzzwords"
    exit 1
}

mkdir -p "$OUTPUT_DIR" "$FAIL_DIR"

DIRECTIVE_CONTENT=$(cat "$IDEA_DIRECTIVE")

echo "============================================================"
echo "FOUNDEROPS IDEA GENERATOR"
echo "============================================================"
echo "Ideas to generate: $NUM_IDEAS"
echo "Directive:         $IDEA_DIRECTIVE"
echo "Output dir:        $OUTPUT_DIR/"
echo "Temperature:       $TEMPERATURE (creative)"
echo "Cost estimate:     ~\$$(echo "scale=3; $NUM_IDEAS * 0.003" | bc)"
echo "============================================================"
echo ""

SUCCESSFUL=0
FAILED=0

for i in $(seq 1 "$NUM_IDEAS"); do

    # Build prompt - include previously generated ideas to avoid duplicates
    EXISTING_IDEAS=""
    if [[ -n "$(ls -A "$OUTPUT_DIR" 2>/dev/null)" ]]; then
        EXISTING_IDEAS="
ALREADY GENERATED (DO NOT REPEAT THESE):
$(ls "$OUTPUT_DIR"/*.txt 2>/dev/null | xargs grep -h '' 2>/dev/null | head -50 || true)"
    fi

    PROMPT="$DIRECTIVE_CONTENT

$EXISTING_IDEAS

Generate idea #$i now. Be creative and different from any existing ideas."

    # Escape for JSON
    ESCAPED_PROMPT="$(printf '%s' "$PROMPT" | jq -Rs .)"

    PAYLOAD=$(cat <<EOF
{
  "model": "$MODEL",
  "max_tokens": $MAX_TOKENS,
  "temperature": $TEMPERATURE,
  "messages": [
    {
      "role": "user",
      "content": $ESCAPED_PROMPT
    }
  ]
}
EOF
)

    # Call API
    RESPONSE=$(curl -s \
        --max-time 30 \
        -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $ANTHROPIC_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        -d "$PAYLOAD")

    # Check for API errors
    if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
        ERR=$(echo "$RESPONSE" | jq -r '.error.message')
        echo "  [$i/$NUM_IDEAS] ✗ API error: $ERR"
        FAILED=$((FAILED + 1))
        sleep $SLEEP_BETWEEN
        continue
    fi

    # Extract text
    TEXT=$(echo "$RESPONSE" | jq -r '.content[0].text // empty')

    if [[ -z "$TEXT" ]]; then
        echo "  [$i/$NUM_IDEAS] ✗ Empty response"
        FAILED=$((FAILED + 1))
        sleep $SLEEP_BETWEEN
        continue
    fi

    # Parse startup_idea_id and description
    IDEA_ID=$(echo "$TEXT" | grep -i "startup_idea_id:" | head -1 \
        | sed 's/.*startup_idea_id://I;s/^ *//;s/ *$//' \
        | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_')

    DESCRIPTION=$(echo "$TEXT" | grep -i "description:" | head -1 \
        | sed 's/.*description://I;s/^ *//;s/ *$//')

    # Fallback if parsing fails
    if [[ -z "$IDEA_ID" ]]; then
        IDEA_ID="idea_$(date +%Y%m%d%H%M%S)_${i}"
    fi
    if [[ -z "$DESCRIPTION" ]]; then
        DESCRIPTION="$TEXT"
    fi

    # Check for duplicate
    IDEA_FILE="$OUTPUT_DIR/${IDEA_ID}.txt"
    if [[ -f "$IDEA_FILE" ]]; then
        echo "  [$i/$NUM_IDEAS] ⚠ Duplicate: $IDEA_ID (skipping)"
        FAILED=$((FAILED + 1))
        sleep $SLEEP_BETWEEN
        continue
    fi

    # Save idea
    echo "$IDEA_ID - $DESCRIPTION" > "$IDEA_FILE"

    SUCCESSFUL=$((SUCCESSFUL + 1))
    echo "  [$i/$NUM_IDEAS] ✅ $IDEA_ID"
    echo "               $DESCRIPTION"

    sleep $SLEEP_BETWEEN
done

# ---- SUMMARY -----------------------------------------------

echo ""
echo "============================================================"
echo "IDEA GENERATION COMPLETE"
echo "============================================================"
echo "Successful: $SUCCESSFUL / $NUM_IDEAS"
echo "Failed:     $FAILED / $NUM_IDEAS"
echo "Output:     $OUTPUT_DIR/"
echo ""
echo "REVIEW:"
echo "  ls $OUTPUT_DIR/"
echo "  cat $OUTPUT_DIR/*.txt"
echo ""
echo "NEXT STEP:"
echo "  Pick ideas you like, then run:"
echo "  ./run_intake.sh 5"
echo "============================================================"

exit 0
