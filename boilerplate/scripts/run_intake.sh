#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# FOUNDEROPS INTAKE RUNNER v6 — TWO-DIRECTIVE ARCHITECTURE
#
# Runs AFTER INTAKE output is ready.
#
# TWO DIRECTIVES:
#   - idea_generation_directive.txt  → creative, temp=1, open-ended
#   - claude_directive.txt           → structured passes, temp=0
#
# TWO PHASES:
#   Phase 1: Generate startup idea (creative, temp=1)
#   Phase 2: Run Block A + Block B passes (deterministic, temp=0)
#
# OUTPUT PER RUN (4 files in run_N/ directory):
#   run_N/block_a.json          ← Tier 1 intake output
#   run_N/block_b.json          ← Tier 2 intake output
#   run_N/{startup_id}.txt      ← One-line startup description
#   run_N/{startup_id}.json     ← Combined block_a + block_b (NOT TRUNCATED)
#
# USAGE:
#   ./run_intake.sh [num_runs] [pass_directive] [idea_directive]
#
# EXAMPLES:
#   ./run_intake.sh               # 5 runs, default directives
#   ./run_intake.sh 20            # 20 runs
#   ./run_intake.sh 10 ./my_directive.txt ./my_idea_directive.txt
#
# REQUIRES:
#   - ANTHROPIC_API_KEY env var
#   - curl, jq
#   - ./inputs/*.json (intake schema files)
#   - claude_directive.txt (pass execution directive)
#   - idea_generation_directive.txt (idea generation directive)
# ============================================================

RUNS="${1:-5}"
PASS_DIRECTIVE="${2:-./claude_directive.txt}"
IDEA_DIRECTIVE="${3:-./idea_generation_directive.txt}"

# ---- CONFIG ------------------------------------------------

INPUTS_DIR="./inputs"
BASE_OUT_DIR="claude_runs"
FAIL_DIR="failures"

MODEL="claude-sonnet-4-5-20250929"
API_URL="https://api.anthropic.com/v1/messages"

# Phase 1: Creative idea generation
IDEA_MAX_TOKENS=500
IDEA_TEMPERATURE=1

# Phase 2: Deterministic pass execution
BLOCK_A_MAX_TOKENS=3000
BLOCK_B_MAX_TOKENS=4096
PASS_TEMPERATURE=0

# Retry settings
MAX_RETRIES=3
RETRY_DELAY=5
RUN_DELAY=10     # seconds between runs (rate limit buffer)

# ---- VALIDATION --------------------------------------------

: "${ANTHROPIC_API_KEY:?ERROR: ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY='sk-ant-...'}"

[[ -f "$PASS_DIRECTIVE" ]] || {
    echo "ERROR: Pass directive not found: $PASS_DIRECTIVE"
    echo "       Create claude_directive.txt or pass path as arg2"
    exit 1
}

[[ -f "$IDEA_DIRECTIVE" ]] || {
    echo "ERROR: Idea directive not found: $IDEA_DIRECTIVE"
    echo "       Create idea_generation_directive.txt or pass path as arg3"
    exit 1
}

[[ -d "$INPUTS_DIR" ]] || {
    echo "ERROR: Inputs directory not found: $INPUTS_DIR"
    echo "       Create ./inputs/ and put your intake schema JSON files in it"
    exit 1
}

JSON_COUNT="$(ls -1 "$INPUTS_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')"
[[ "$JSON_COUNT" -ge 1 ]] || {
    echo "ERROR: No JSON files found in $INPUTS_DIR"
    exit 1
}

mkdir -p "$BASE_OUT_DIR" "$FAIL_DIR"

echo "============================================================"
echo "FOUNDEROPS INTAKE RUNNER v6"
echo "============================================================"
echo "Runs:           $RUNS"
echo "Pass directive: $PASS_DIRECTIVE"
echo "Idea directive: $IDEA_DIRECTIVE"
echo "Inputs dir:     $INPUTS_DIR ($JSON_COUNT files)"
echo "Output dir:     $BASE_OUT_DIR"
echo "Model:          $MODEL"
echo "Phase 1:        temp=$IDEA_TEMPERATURE (creative idea)"
echo "Phase 2:        temp=$PASS_TEMPERATURE (deterministic passes)"
echo "============================================================"

# ---- HELPERS -----------------------------------------------

# Build the base bundle from all input JSON files
build_base_bundle() {
    local f
    for f in "$INPUTS_DIR"/*.json; do
        echo "===== BEGIN FILE: $(basename "$f") ====="
        cat "$f"
        echo
        echo "===== END FILE: $(basename "$f") ====="
        echo
    done
}

# Call Claude API with given prompt, max_tokens, temperature
call_claude() {
    local prompt="$1"
    local max_tokens="$2"
    local temperature="$3"
    local escaped_prompt

    escaped_prompt="$(printf '%s' "$prompt" | jq -Rs .)"

    local payload
    payload=$(cat <<EOF
{
  "model": "$MODEL",
  "max_tokens": $max_tokens,
  "temperature": $temperature,
  "messages": [
    {
      "role": "user",
      "content": $escaped_prompt
    }
  ]
}
EOF
)

    curl -s \
        --max-time 120 \
        -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $ANTHROPIC_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        -d "$payload"
}

# Extract text content from Claude response
extract_text() {
    local response="$1"
    echo "$response" | jq -r '.content[0].text // empty'
}

# Extract JSON block from a text response
extract_json_block() {
    local text="$1"
    # Try to find JSON between ```json and ``` markers first
    if echo "$text" | grep -q '```json'; then
        echo "$text" | sed -n '/```json/,/```/p' | sed '1d;$d'
    # Then try bare { ... } extraction
    elif echo "$text" | grep -q '^{'; then
        echo "$text"
    else
        # Try to extract any JSON object
        echo "$text" | python3 -c "
import sys, re, json
text = sys.stdin.read()
matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
for m in matches:
    try:
        json.loads(m)
        print(m)
        break
    except:
        pass
"
    fi
}

# Run a block with retry logic
run_block_with_retry() {
    local block_name="$1"   # "A" or "B"
    local prompt="$2"
    local max_tokens="$3"
    local output_file="$4"

    local attempt=1
    local response text json_data

    while [[ $attempt -le $MAX_RETRIES ]]; do
        echo "  [Block $block_name] Attempt $attempt/$MAX_RETRIES..."

        response=$(call_claude "$prompt" "$max_tokens" "$PASS_TEMPERATURE")

        # Check for API errors
        if echo "$response" | jq -e '.error' > /dev/null 2>&1; then
            echo "  [Block $block_name] API error: $(echo "$response" | jq -r '.error.message')"
            attempt=$((attempt + 1))
            sleep $RETRY_DELAY
            continue
        fi

        text=$(extract_text "$response")

        if [[ -z "$text" ]]; then
            echo "  [Block $block_name] Empty response"
            attempt=$((attempt + 1))
            sleep $RETRY_DELAY
            continue
        fi

        json_data=$(extract_json_block "$text")

        if jq empty <<< "$json_data" 2>/dev/null; then
            echo "$json_data" > "$output_file"
            echo "  [Block $block_name] ✓ Success"

            # Show token usage
            local in_tokens out_tokens
            in_tokens=$(echo "$response" | jq -r '.usage.input_tokens // 0')
            out_tokens=$(echo "$response" | jq -r '.usage.output_tokens // 0')
            echo "  [Block $block_name] Tokens: in=$in_tokens out=$out_tokens"

            # Warn if truncated
            local stop_reason
            stop_reason=$(echo "$response" | jq -r '.stop_reason // "unknown"')
            if [[ "$stop_reason" == "max_tokens" ]]; then
                echo "  [Block $block_name] ⚠ WARNING: Output truncated (hit max_tokens)"
            fi

            return 0
        else
            echo "  [Block $block_name] Invalid JSON on attempt $attempt"
            attempt=$((attempt + 1))
            sleep $RETRY_DELAY
        fi
    done

    echo "  [Block $block_name] ✗ Failed after $MAX_RETRIES attempts"
    return 1
}

# ---- MAIN LOOP ---------------------------------------------

PASS_DIRECTIVE_CONTENT=$(cat "$PASS_DIRECTIVE")
IDEA_DIRECTIVE_CONTENT=$(cat "$IDEA_DIRECTIVE")
BASE_BUNDLE=$(build_base_bundle)

SUCCESSFUL=0
FAILED=0

for i in $(seq 1 "$RUNS"); do
    echo ""
    echo "============================================================"
    echo "RUN $i / $RUNS"
    echo "============================================================"

    RUN_DIR="$BASE_OUT_DIR/run_$i"
    mkdir -p "$RUN_DIR"

    # ----------------------------------------------------------
    # PHASE 1: GENERATE STARTUP IDEA (temp=1, creative)
    # ----------------------------------------------------------

    echo "  [Phase 1] Generating startup idea (temp=$IDEA_TEMPERATURE)..."

    IDEA_PROMPT="$IDEA_DIRECTIVE_CONTENT

$BASE_BUNDLE

Generate ONE startup idea now. Follow the format exactly."

    IDEA_RESPONSE=$(call_claude "$IDEA_PROMPT" "$IDEA_MAX_TOKENS" "$IDEA_TEMPERATURE")

    if echo "$IDEA_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
        echo "  [Phase 1] API error: $(echo "$IDEA_RESPONSE" | jq -r '.error.message')"
        FAILED=$((FAILED + 1))
        continue
    fi

    IDEA_TEXT=$(extract_text "$IDEA_RESPONSE")

    if [[ -z "$IDEA_TEXT" ]]; then
        echo "  [Phase 1] Empty idea response"
        FAILED=$((FAILED + 1))
        continue
    fi

    # Extract startup_idea_id and one-liner from idea response
    # Expected format: STARTUP_IDEA_ID: xxx\nDESCRIPTION: one liner
    STARTUP_ID=$(echo "$IDEA_TEXT" | grep -i "startup_idea_id:" | head -1 | sed 's/.*://;s/^ *//;s/ *$//' | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
    DESCRIPTION=$(echo "$IDEA_TEXT" | grep -i "description:" | head -1 | sed 's/.*description://I;s/^ *//;s/ *$//')

    # Fallback: use run number if parsing fails
    if [[ -z "$STARTUP_ID" ]]; then
        STARTUP_ID="startup_$(date +%Y%m%d)_run_${i}"
    fi
    if [[ -z "$DESCRIPTION" ]]; then
        DESCRIPTION="$IDEA_TEXT"
    fi

    echo "  [Phase 1] ✓ Idea: $STARTUP_ID"
    echo "  [Phase 1]   $DESCRIPTION"

    # Save one-liner .txt file
    IDEA_TXT_FILE="$RUN_DIR/${STARTUP_ID}.txt"
    echo "$STARTUP_ID - $DESCRIPTION" > "$IDEA_TXT_FILE"

    # ----------------------------------------------------------
    # PHASE 2: BLOCK A — TIER 1 PASSES (temp=0, deterministic)
    # ----------------------------------------------------------

    echo "  [Phase 2] Running Block A (Tier 1, temp=$PASS_TEMPERATURE)..."

    JSON_A="$RUN_DIR/block_a.json"

    PROMPT_A="$PASS_DIRECTIVE_CONTENT

===== STARTUP IDEA =====
startup_idea_id: $STARTUP_ID
description: $DESCRIPTION

===== INPUT FILES =====
$BASE_BUNDLE

Execute BLOCK A (Tier 1) passes for this startup idea.
Output ONLY valid JSON. No truncation. No markdown fences."

    if ! run_block_with_retry "A" "$PROMPT_A" "$BLOCK_A_MAX_TOKENS" "$JSON_A"; then
        echo "  ✗ Block A failed - skipping run $i"
        mv "$RUN_DIR" "$FAIL_DIR/run_${i}_failed"
        FAILED=$((FAILED + 1))
        continue
    fi

    # ----------------------------------------------------------
    # PHASE 2: BLOCK B — TIER 2 PASSES (temp=0, deterministic)
    # Uses SAME startup_idea_id as Block A
    # ----------------------------------------------------------

    echo "  [Phase 2] Running Block B (Tier 2, temp=$PASS_TEMPERATURE)..."

    JSON_B="$RUN_DIR/block_b.json"

    PROMPT_B="$PASS_DIRECTIVE_CONTENT

===== STARTUP IDEA (SAME AS BLOCK A) =====
startup_idea_id: $STARTUP_ID
description: $DESCRIPTION

===== BLOCK A OUTPUT =====
$(cat "$JSON_A")

===== INPUT FILES =====
$BASE_BUNDLE

Execute BLOCK B (Tier 2 expansion) passes for the SAME startup idea above.
CRITICAL: Use the SAME startup_idea_id: $STARTUP_ID
Output ONLY valid JSON. No truncation. No markdown fences."

    if ! run_block_with_retry "B" "$PROMPT_B" "$BLOCK_B_MAX_TOKENS" "$JSON_B"; then
        echo "  ✗ Block B failed - keeping Block A, marking partial"
        FAILED=$((FAILED + 1))
        continue
    fi

    # ----------------------------------------------------------
    # COMBINE BLOCK A + BLOCK B INTO {startup_id}.json
    # ----------------------------------------------------------

    COMBINED_JSON="$RUN_DIR/${STARTUP_ID}.json"

    jq -n \
        --arg run_id "run_$i" \
        --arg startup_idea_id "$STARTUP_ID" \
        --arg description "$DESCRIPTION" \
        --slurpfile block_a "$JSON_A" \
        --slurpfile block_b "$JSON_B" \
        '{
            run_id: $run_id,
            startup_idea_id: $startup_idea_id,
            description: $description,
            block_a: $block_a[0],
            block_b: $block_b[0]
        }' > "$COMBINED_JSON"

    # Validate combined JSON
    if ! jq empty "$COMBINED_JSON" 2>/dev/null; then
        echo "  ✗ Combined JSON invalid"
        FAILED=$((FAILED + 1))
        continue
    fi

    echo ""
    echo "  ✅ RUN $i COMPLETE: $STARTUP_ID"
    echo "     $RUN_DIR/"
    echo "     ├── block_a.json"
    echo "     ├── block_b.json"
    echo "     ├── ${STARTUP_ID}.txt"
    echo "     └── ${STARTUP_ID}.json"

    SUCCESSFUL=$((SUCCESSFUL + 1))

    # Rate limit buffer between runs
    if [[ $i -lt $RUNS ]]; then
        echo "  [Waiting ${RUN_DELAY}s before next run...]"
        sleep $RUN_DELAY
    fi
done

# ---- SUMMARY -----------------------------------------------

echo ""
echo "============================================================"
echo "ALL RUNS COMPLETE"
echo "============================================================"
echo "Successful: $SUCCESSFUL / $RUNS"
echo "Failed:     $FAILED / $RUNS"
echo "Output:     $BASE_OUT_DIR/"
echo ""
echo "REVIEW:"
echo "  ls $BASE_OUT_DIR/"
echo "  cat $BASE_OUT_DIR/run_1/*.txt"
echo "  cat $BASE_OUT_DIR/run_1/*.json | jq '.startup_idea_id'"
echo "============================================================"

exit 0
