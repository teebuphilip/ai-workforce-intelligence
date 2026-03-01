#!/bin/bash
############################################################
# FO BUILD + DEPLOY EXECUTOR
# Usage: ./fo_build_executor.sh <intake_json_file>
#
# Takes 1 input:  intake JSON (BLOCK_A / BLOCK_B format)
# Reads 2 zips:   BUILD governance + DEPLOY governance
# Calls Claude:   with max tokens to prevent truncation
# Saves output:   all artifacts to timestamped run directory
############################################################

set -e  # Exit on any error

# ---- COLOR CODES ----------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ---- CONFIGURATION (UPDATE THESE) -----------------------

# Governance zip locations - set to your local paths
BUILD_GOVERNANCE_ZIP="/path/to/FOBUILFINALLOCKED100.zip"
DEPLOY_GOVERNANCE_ZIP="/path/to/fo_deploy_governance_v1_2_CLARIFIED.zip"

# Claude API settings
CLAUDE_MODEL="claude-sonnet-4-5-20250929"
MAX_TOKENS=200000          # Prevent truncation - use max

# Output directory
OUTPUT_BASE_DIR="$(pwd)/fo_runs"

# ---- FUNCTIONS ------------------------------------------

print_header() {
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}  $1${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}>>> $1${NC}"
}

print_ok() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ ERROR: $1${NC}" >&2
}

check_file() {
    if [ ! -f "$1" ]; then
        print_error "File not found: $1"
        exit 1
    fi
}

check_dependencies() {
    local missing=0

    if ! command -v curl &> /dev/null; then
        print_error "curl not found. Install: brew install curl"
        missing=1
    fi

    if ! command -v jq &> /dev/null; then
        print_error "jq not found. Install: brew install jq"
        missing=1
    fi

    if ! command -v base64 &> /dev/null; then
        print_error "base64 not found (should be built-in on macOS/Linux)"
        missing=1
    fi

    if [ -z "$ANTHROPIC_API_KEY" ]; then
        print_error "ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY='sk-ant-...'"
        missing=1
    fi

    if [ "$missing" -eq 1 ]; then
        exit 1
    fi
}

encode_file_base64() {
    # Encode a file to base64 (works on both macOS and Linux)
    base64 -i "$1" 2>/dev/null || base64 "$1"
}

# ---- MAIN -----------------------------------------------

print_header "FO BUILD + DEPLOY EXECUTOR"

# ---- ARGUMENT CHECK -------------------------------------

if [ $# -ne 1 ]; then
    echo ""
    echo "Usage:   $0 <intake_json_file>"
    echo ""
    echo "Example: $0 inboxtamer_intake.json"
    echo "         $0 /path/to/watercooler_iteration_9.json"
    echo ""
    echo "The intake JSON must be MCv6-SCHEMA v21.4 format"
    echo "with BLOCK_A and BLOCK_B sections."
    echo ""
    exit 1
fi

INTAKE_FILE="$1"

# ---- VALIDATION -----------------------------------------

print_step "Validating inputs..."

check_file "$INTAKE_FILE"
check_file "$BUILD_GOVERNANCE_ZIP"
check_file "$DEPLOY_GOVERNANCE_ZIP"
check_dependencies

print_ok "All inputs validated"

# ---- EXTRACT METADATA -----------------------------------

STARTUP_ID=$(jq -r '.startup_idea_id // "unknown_startup"' "$INTAKE_FILE")
STARTUP_NAME=$(jq -r '.BLOCK_A.startup_name // .startup_name // "Unknown"' "$INTAKE_FILE")
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_DIR="${OUTPUT_BASE_DIR}/${STARTUP_ID}_${TIMESTAMP}"

print_step "Startup: $STARTUP_NAME ($STARTUP_ID)"
print_step "Run directory: $RUN_DIR"

# Create run directory
mkdir -p "$RUN_DIR"

# Copy intake file into run directory for record
cp "$INTAKE_FILE" "$RUN_DIR/intake_input.json"

# ---- ENCODE FILES FOR API -------------------------------

print_step "Encoding governance files..."

BUILD_ZIP_B64=$(encode_file_base64 "$BUILD_GOVERNANCE_ZIP")
DEPLOY_ZIP_B64=$(encode_file_base64 "$DEPLOY_GOVERNANCE_ZIP")
INTAKE_CONTENT=$(cat "$INTAKE_FILE")

print_ok "Files encoded"

# ---- BUILD BLOCK_A --------------------------------------

print_header "STEP 1: BUILD PHASE — BLOCK_A (Tier 1)"

BUILD_PROMPT="You are the FO BUILD EXECUTOR running in FOUNDER_FAST_PATH mode.

INTAKE DATA (MCv6-SCHEMA v21.4):
${INTAKE_CONTENT}

YOUR TASK:
1. Read the FO Build Governance from the attached FOBUILFINALLOCKED100.zip
2. Extract BLOCK_A from the intake data above
3. Execute BUILD for Tier 1 according to fo_build_state_machine.json
4. Follow ALL enforcement rules (tier, scope, iteration limits)
5. Produce COMPLETED_CLOSED state with all required artifacts

CRITICAL RULES:
- No inference - follow governance literally
- Max 5 iterations per task
- No scope changes without explicit protocol
- Produce all required artifacts:
  * artifact_manifest.json (with SHA256 checksums)
  * build_state.json (state = COMPLETED_CLOSED)
  * execution_declaration.json (all commands)
  * All code files complete and non-truncated
  * QA checklist

OUTPUT REQUIREMENTS:
- Provide complete code files - NO truncated snippets
- Every file must be fully written out
- Use code blocks for all files
- Label each file clearly with its path

Begin BUILD execution now."

# Build the JSON payload
# NOTE: Attaching zips as base64 documents
BUILD_PAYLOAD=$(jq -n \
    --arg model "$CLAUDE_MODEL" \
    --argjson max_tokens "$MAX_TOKENS" \
    --arg prompt "$BUILD_PROMPT" \
    --arg build_zip "$BUILD_ZIP_B64" \
    --arg deploy_zip "$DEPLOY_ZIP_B64" \
    '{
        model: $model,
        max_tokens: $max_tokens,
        messages: [
            {
                role: "user",
                content: [
                    {
                        type: "document",
                        source: {
                            type: "base64",
                            media_type: "application/zip",
                            data: $build_zip
                        },
                        title: "FOBUILFINALLOCKED100.zip"
                    },
                    {
                        type: "document",
                        source: {
                            type: "base64",
                            media_type: "application/zip",
                            data: $deploy_zip
                        },
                        title: "fo_deploy_governance_v1_2_CLARIFIED.zip"
                    },
                    {
                        type: "text",
                        text: $prompt
                    }
                ]
            }
        ]
    }')

print_step "Calling Claude API for BLOCK_A build..."
print_warn "This may take several minutes for large builds..."

# Make the API call
BUILD_RESPONSE=$(curl -s \
    --max-time 600 \
    -X POST "https://api.anthropic.com/v1/messages" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -d "$BUILD_PAYLOAD")

# Check for API errors
if echo "$BUILD_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    print_error "Claude API error:"
    echo "$BUILD_RESPONSE" | jq '.error'
    exit 1
fi

# Extract and save output
BUILD_OUTPUT=$(echo "$BUILD_RESPONSE" | jq -r '.content[0].text // "NO OUTPUT"')
INPUT_TOKENS=$(echo "$BUILD_RESPONSE" | jq -r '.usage.input_tokens // 0')
OUTPUT_TOKENS=$(echo "$BUILD_RESPONSE" | jq -r '.usage.output_tokens // 0')
STOP_REASON=$(echo "$BUILD_RESPONSE" | jq -r '.stop_reason // "unknown"')

# Save all artifacts
echo "$BUILD_OUTPUT" > "$RUN_DIR/build_output_block_a.txt"
echo "$BUILD_RESPONSE" > "$RUN_DIR/build_response_raw_block_a.json"

print_ok "BLOCK_A build complete"
echo "  Input tokens:  $INPUT_TOKENS"
echo "  Output tokens: $OUTPUT_TOKENS"
echo "  Stop reason:   $STOP_REASON"
echo "  Output saved:  $RUN_DIR/build_output_block_a.txt"

# Warn if truncated
if [ "$STOP_REASON" = "max_tokens" ]; then
    print_warn "Output was TRUNCATED (hit max_tokens limit)"
    print_warn "Consider splitting into smaller tasks"
fi

# ---- BUILD BLOCK_B --------------------------------------

print_header "STEP 2: BUILD PHASE — BLOCK_B (Tier 2)"

BUILD_B_PROMPT="You are the FO BUILD EXECUTOR running in FOUNDER_FAST_PATH mode.

INTAKE DATA (MCv6-SCHEMA v21.4):
${INTAKE_CONTENT}

BLOCK_A BUILD RESULTS:
$(cat "$RUN_DIR/build_output_block_a.txt")

YOUR TASK:
1. Read the FO Build Governance from the attached FOBUILFINALLOCKED100.zip
2. Extract BLOCK_B from the intake data above
3. Execute BUILD for Tier 2 - building ON TOP of BLOCK_A
4. Follow ALL enforcement rules
5. Produce COMPLETED_CLOSED state with all required artifacts

CRITICAL RULES:
- BLOCK_A is already complete - do not rebuild it
- Build ONLY what BLOCK_B requires
- Produce all artifacts
- No truncated output

Begin BLOCK_B BUILD execution now."

BUILD_B_PAYLOAD=$(jq -n \
    --arg model "$CLAUDE_MODEL" \
    --argjson max_tokens "$MAX_TOKENS" \
    --arg prompt "$BUILD_B_PROMPT" \
    --arg build_zip "$BUILD_ZIP_B64" \
    '{
        model: $model,
        max_tokens: $max_tokens,
        messages: [
            {
                role: "user",
                content: [
                    {
                        type: "document",
                        source: {
                            type: "base64",
                            media_type: "application/zip",
                            data: $build_zip
                        },
                        title: "FOBUILFINALLOCKED100.zip"
                    },
                    {
                        type: "text",
                        text: $prompt
                    }
                ]
            }
        ]
    }')

print_step "Calling Claude API for BLOCK_B build..."

BUILD_B_RESPONSE=$(curl -s \
    --max-time 600 \
    -X POST "https://api.anthropic.com/v1/messages" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -d "$BUILD_B_PAYLOAD")

if echo "$BUILD_B_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    print_error "Claude API error on BLOCK_B:"
    echo "$BUILD_B_RESPONSE" | jq '.error'
    exit 1
fi

BUILD_B_OUTPUT=$(echo "$BUILD_B_RESPONSE" | jq -r '.content[0].text // "NO OUTPUT"')
B_STOP_REASON=$(echo "$BUILD_B_RESPONSE" | jq -r '.stop_reason // "unknown"')

echo "$BUILD_B_OUTPUT" > "$RUN_DIR/build_output_block_b.txt"
echo "$BUILD_B_RESPONSE" > "$RUN_DIR/build_response_raw_block_b.json"

print_ok "BLOCK_B build complete"
echo "  Stop reason: $B_STOP_REASON"
echo "  Output saved: $RUN_DIR/build_output_block_b.txt"

if [ "$B_STOP_REASON" = "max_tokens" ]; then
    print_warn "BLOCK_B output was TRUNCATED"
fi

# ---- DEPLOY ---------------------------------------------

print_header "STEP 3: DEPLOY PHASE"

DEPLOY_PROMPT="You are the FO DEPLOY EXECUTOR.

STARTUP: $STARTUP_NAME ($STARTUP_ID)

BLOCK_A BUILD:
$(cat "$RUN_DIR/build_output_block_a.txt")

BLOCK_B BUILD:
$(cat "$RUN_DIR/build_output_block_b.txt")

YOUR TASK:
1. Read the FO Deploy Governance from fo_deploy_governance_v1_2_CLARIFIED.zip
2. Execute DEPLOY for this startup
3. Produce all deployment artifacts:
   * deployment_manifest.json
   * deployment_state.json (state = DEPLOYED)
   * All infrastructure-as-code files
   * All environment configuration
   * Post-deployment verification checklist

CRITICAL:
- Complete output only - no truncation
- All files fully written out

Begin DEPLOY execution now."

DEPLOY_PAYLOAD=$(jq -n \
    --arg model "$CLAUDE_MODEL" \
    --argjson max_tokens "$MAX_TOKENS" \
    --arg prompt "$DEPLOY_PROMPT" \
    --arg deploy_zip "$DEPLOY_ZIP_B64" \
    '{
        model: $model,
        max_tokens: $max_tokens,
        messages: [
            {
                role: "user",
                content: [
                    {
                        type: "document",
                        source: {
                            type: "base64",
                            media_type: "application/zip",
                            data: $deploy_zip
                        },
                        title: "fo_deploy_governance_v1_2_CLARIFIED.zip"
                    },
                    {
                        type: "text",
                        text: $prompt
                    }
                ]
            }
        ]
    }')

print_step "Calling Claude API for DEPLOY..."

DEPLOY_RESPONSE=$(curl -s \
    --max-time 600 \
    -X POST "https://api.anthropic.com/v1/messages" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -d "$DEPLOY_PAYLOAD")

if echo "$DEPLOY_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    print_error "Claude API error on DEPLOY:"
    echo "$DEPLOY_RESPONSE" | jq '.error'
    exit 1
fi

DEPLOY_OUTPUT=$(echo "$DEPLOY_RESPONSE" | jq -r '.content[0].text // "NO OUTPUT"')
DEPLOY_STOP=$(echo "$DEPLOY_RESPONSE" | jq -r '.stop_reason // "unknown"')

echo "$DEPLOY_OUTPUT" > "$RUN_DIR/deploy_output.txt"
echo "$DEPLOY_RESPONSE" > "$RUN_DIR/deploy_response_raw.json"

print_ok "DEPLOY complete"
echo "  Stop reason: $DEPLOY_STOP"
echo "  Output saved: $RUN_DIR/deploy_output.txt"

# ---- SUMMARY --------------------------------------------

print_header "RUN COMPLETE"

echo "Startup:     $STARTUP_NAME ($STARTUP_ID)"
echo "Run dir:     $RUN_DIR"
echo ""
echo "Artifacts:"
ls -lh "$RUN_DIR/"
echo ""

# Write run manifest
cat > "$RUN_DIR/run_manifest.json" << MANIFEST
{
  "startup_id": "$STARTUP_ID",
  "startup_name": "$STARTUP_NAME",
  "timestamp": "$TIMESTAMP",
  "intake_file": "$INTAKE_FILE",
  "build_governance": "$BUILD_GOVERNANCE_ZIP",
  "deploy_governance": "$DEPLOY_GOVERNANCE_ZIP",
  "model": "$CLAUDE_MODEL",
  "artifacts": {
    "build_a": "build_output_block_a.txt",
    "build_b": "build_output_block_b.txt",
    "deploy": "deploy_output.txt"
  },
  "stop_reasons": {
    "block_a": "$STOP_REASON",
    "block_b": "$B_STOP_REASON",
    "deploy": "$DEPLOY_STOP"
  }
}
MANIFEST

print_ok "Run manifest saved: $RUN_DIR/run_manifest.json"
echo ""
echo -e "${GREEN}All done. Review artifacts in: $RUN_DIR${NC}"
echo ""
