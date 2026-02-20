#!/bin/bash
# Skill Trending Monitor - Weekly Report Wrapper
# Runs comprehensive analysis + sends Telegram summary
# Schedule: Every Sunday 10:00 (crontab)

set -euo pipefail

if [ -z "${HOME:-}" ]; then
    HOME="$(cd ~ && pwd)"
    export HOME
fi
export PATH="/usr/local/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

PROJECT_ROOT="${PDT_PROJECT_ROOT:-$HOME/Workspace/Personal-Digital-Twin}"
if [ ! -d "$PROJECT_ROOT" ]; then
    echo "ERROR: PROJECT_ROOT does not exist: $PROJECT_ROOT" >&2
    exit 1
fi
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd -P)"
cd "$PROJECT_ROOT"

SKILL_DIR="$HOME/.claude/skills/skill-trending-monitor-cskill"
SCRIPTS_DIR="$SKILL_DIR/scripts"
LOG_FILE="logs/skill-trending-weekly.log"
TELEGRAPH_SCRIPT=".claude/skills/cog-daily-brief/scripts/publish-to-telegraph.py"
TELEGRAM_SCRIPT="scripts/notify-telegram.sh"
JOBS_FILE="digital-twin-viz/public/data/scheduled-jobs.json"
TELEGRAPH_VERIFY_TIMEOUT_SEC="${TELEGRAPH_VERIFY_TIMEOUT_SEC:-10}"

if ! [[ "$TELEGRAPH_VERIFY_TIMEOUT_SEC" =~ ^[0-9]+$ ]] || [ "$TELEGRAPH_VERIFY_TIMEOUT_SEC" -lt 1 ] || [ "$TELEGRAPH_VERIFY_TIMEOUT_SEC" -gt 60 ]; then
    TELEGRAPH_VERIFY_TIMEOUT_SEC=10
fi

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

update_job_status() {
    local status="$1"
    local doc_path="${2:-}"
    if [ -f "$JOBS_FILE" ]; then
        if ! command -v jq >/dev/null 2>&1; then
            log "WARNING: jq not found, skipping job status update"
            return 0
        fi
        local tmp_file
        tmp_file="$(mktemp "${JOBS_FILE}.tmp.XXXXXX")"
        local jq_ok=0
        if [ -n "$doc_path" ]; then
            if jq --arg status "$status" \
               --arg timestamp "$(date +%Y-%m-%dT%H:%M:%S)" \
               --arg doc "$doc_path" \
               '(.jobs[] | select(.id == "skill-trending-weekly")) |= . + {lastRun: $timestamp, lastStatus: $status, documentationPath: $doc}' \
               "$JOBS_FILE" > "$tmp_file"; then
                jq_ok=1
            fi
        else
            if jq --arg status "$status" \
               --arg timestamp "$(date +%Y-%m-%dT%H:%M:%S)" \
               '(.jobs[] | select(.id == "skill-trending-weekly")) |= . + {lastRun: $timestamp, lastStatus: $status}' \
               "$JOBS_FILE" > "$tmp_file"; then
                jq_ok=1
            fi
        fi
        if [ "$jq_ok" -ne 1 ]; then
            rm -f "$tmp_file"
            log "WARNING: Failed to render updated job status via jq"
            return 0
        fi
        if mv "$tmp_file" "$JOBS_FILE"; then
            log "Job status updated: $status"
        else
            rm -f "$tmp_file"
            log "WARNING: Failed to move updated job status file"
        fi
    fi
}

send_telegram() {
    local msg="$1"
    local parse_mode="${2:-}"
    if [ -f "$TELEGRAM_SCRIPT" ]; then
        bash "$TELEGRAM_SCRIPT" "$msg" "$parse_mode" || true
    fi
}

verify_telegraph_url() {
    local url="$1"
    if [ -z "$url" ]; then
        return 1
    fi
    case "$url" in
        https://telegra.ph/*) ;;
        *)
            log "WARNING: Telegraph URL rejected (invalid host): $url"
            return 1
            ;;
    esac
    if [[ "$url" == *$'\n'* || "$url" == *$'\r'* ]] || printf '%s' "$url" | grep -Eq "[[:space:]<>()\\[\\]'\\\"]" ; then
        log "WARNING: Telegraph URL rejected (contains unsafe characters)"
        return 1
    fi
    if ! command -v curl >/dev/null 2>&1; then
        return 1
    fi

    local http_code
    http_code=$(curl -sS --proto '=https' --max-redirs 0 -m "$TELEGRAPH_VERIFY_TIMEOUT_SEC" -o /dev/null -w "%{http_code}" -- "$url" 2>/dev/null || true)
    if [[ "$http_code" =~ ^2 ]]; then
        return 0
    fi

    log "WARNING: Telegraph URL verification failed (code=${http_code:-unknown}): $url"
    return 1
}

log "========== Skill Trending Weekly Report =========="

# ---- Step 1: Run comprehensive analysis ----
log "Step 1: Running comprehensive analysis..."

REPORT_DATE=$(date +%Y-%m-%d)
REPORT_PATH="$SKILL_DIR/meta/reports/${REPORT_DATE}-skill-trending-report.md"
ANALYSIS_PROFILE="${SKILL_TRENDING_PROFILE:-strict}"
case "$ANALYSIS_PROFILE" in
    strict|balanced|permissive|experimental) ;;
    *)
        log "ERROR: Invalid ANALYSIS_PROFILE '$ANALYSIS_PROFILE'"
        update_job_status "failed"
        exit 1
        ;;
esac

# Activate venv if exists
if [ -d "$SKILL_DIR/.venv" ]; then
    # shellcheck disable=SC1091
    source "$SKILL_DIR/.venv/bin/activate" || true
fi

run_analysis() {
    python3 "$SCRIPTS_DIR/analyze_comprehensive.py" --profile "$ANALYSIS_PROFILE" 2>&1 | tee -a "$LOG_FILE"
}

if run_analysis; then
    log "Analysis completed successfully"
else
    log "WARNING: First analysis attempt failed; retrying once after 10s..."
    sleep 10
    if run_analysis; then
        log "Analysis completed successfully on retry"
    else
        log "ERROR: Analysis failed"
        send_telegram "❌ Skill Trending 周报失败

Error: analyze_comprehensive.py 执行出错
Profile: ${ANALYSIS_PROFILE}
Time: $(date '+%Y-%m-%d %H:%M:%S')
Check: logs/skill-trending-weekly.log"
        update_job_status "failed"
        exit 1
    fi
fi

# ---- Step 2: Find the generated report ----
if [ ! -f "$REPORT_PATH" ]; then
    # Try to find the report (it may have been generated to skill dir's meta/reports)
    REPORT_PATH=$(find "$SKILL_DIR/meta/reports" -name "${REPORT_DATE}*skill-trending*" -type f 2>/dev/null | head -1)
fi

if [ -z "$REPORT_PATH" ] || [ ! -f "$REPORT_PATH" ]; then
    log "ERROR: Report file not found"
    send_telegram "❌ Skill Trending 周报失败

Error: 报告文件未生成
Time: $(date '+%Y-%m-%d %H:%M:%S')"
    update_job_status "failed"
    exit 1
fi

log "Report found: $REPORT_PATH"

# ---- Step 3: Copy report to PDT meta/reports ----
PDT_REPORT="meta/reports/${REPORT_DATE}-skill-trending-report.md"
mkdir -p "meta/reports"
cp "$REPORT_PATH" "$PDT_REPORT"
log "Report copied to: $PDT_REPORT"

# ---- Step 4: Extract summary for Telegram ----
log "Step 4: Extracting summary..."

# Extract key metrics from the report
NEW_SKILLS=$(grep -c "^####" "$PDT_REPORT" 2>/dev/null || echo "0")
TOTAL_SKILLS=$(grep -i "total.*skill" "$PDT_REPORT" | head -1 || echo "31,767")
REPORT_DIR="${PROJECT_ROOT}/meta/reports"
TELEGRAPH_URL=""
TELEGRAPH_OUTPUT=""
if [ -f "$TELEGRAPH_SCRIPT" ] && command -v python3 >/dev/null 2>&1; then
    if TELEGRAPH_OUTPUT=$(python3 "$TELEGRAPH_SCRIPT" "$PDT_REPORT" "Skill Trending 周报 ${REPORT_DATE}" 2>&1); then
        TELEGRAPH_URL=$(printf '%s\n' "$TELEGRAPH_OUTPUT" | tail -n 1)
        if verify_telegraph_url "$TELEGRAPH_URL"; then
            log "Telegraph published and verified: $TELEGRAPH_URL"
        else
            TELEGRAPH_URL=""
            log "WARNING: Telegraph publish succeeded but URL verification failed"
        fi
    else
        log "WARNING: Telegraph publish failed"
        if [ -n "$TELEGRAPH_OUTPUT" ]; then
            printf '%s\n' "$TELEGRAPH_OUTPUT" | tail -n 20 | sed 's/^/[TELEGRAPH] /' | tee -a "$LOG_FILE" >/dev/null
        fi
        TELEGRAPH_URL=""
    fi
else
    log "WARNING: Telegraph script or python3 not found"
fi

SUMMARY="📊 Skill Trending 周报 (${REPORT_DATE})

🔍 分析完成
• 数据源: skill-manager + GitHub API
• 分析模式: ${ANALYSIS_PROFILE}

📋 概要:
• 新发现 Skills: ~${NEW_SKILLS} 个推荐
• 数据库总量: ${TOTAL_SKILLS}

📁 报告目录: ${REPORT_DIR}
🧭 打开命令: open ${REPORT_DIR}"

if [ -n "$TELEGRAPH_URL" ]; then
    SUMMARY="${SUMMARY}
🔗 在线阅读: ${TELEGRAPH_URL}"
fi

# ---- Step 5: Send Telegram notification ----
log "Step 5: Sending Telegram..."

CHAR_COUNT=${#SUMMARY}
if [ "$CHAR_COUNT" -le 3900 ]; then
    send_telegram "$SUMMARY"
    log "Telegram summary sent (${CHAR_COUNT} chars)"
else
    log "Summary too long (${CHAR_COUNT} chars), sending shortened version"
    if [ -n "$TELEGRAPH_URL" ]; then
        SHORT_SUMMARY="📊 Skill Trending 周报 (${REPORT_DATE})
🔗 在线阅读: ${TELEGRAPH_URL}
📁 报告目录: ${REPORT_DIR}
🧭 打开命令: open ${REPORT_DIR}"
        send_telegram "$SHORT_SUMMARY"
    else
        TRUNCATED="${SUMMARY:0:3900}..."
        send_telegram "$TRUNCATED"
    fi
fi

# ---- Step 6: Monthly market discovery (first Sunday of month) ----
DAY_OF_MONTH=$(date +%d)
if [ "$DAY_OF_MONTH" -le 7 ]; then
    log "Step 6: First Sunday of month — running market discovery..."
    MARKETS_SCRIPT="$SCRIPTS_DIR/discover_markets.py"
    if [ -f "$MARKETS_SCRIPT" ]; then
        if python3 "$MARKETS_SCRIPT" 2>&1 | tee -a "$LOG_FILE"; then
            log "Market discovery completed"
        else
            log "WARNING: Market discovery failed (non-fatal)"
        fi
    else
        log "WARNING: discover_markets.py not found, skipping"
    fi
else
    log "Step 6: Skipping market discovery (not first Sunday)"
fi

# ---- Step 7: Update job status ----
update_job_status "success" "$PDT_REPORT"

log "========== Weekly Report Complete =========="
log "Report: $PDT_REPORT"
