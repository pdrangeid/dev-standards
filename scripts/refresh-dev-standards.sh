#!/bin/bash
# =============================================================================
# refresh-dev-standards.sh — Update auto-generated sections of AGENTS.md
#
# Usage:
#   ./refresh-dev-standards.sh [--agents-md <path>] [--dry-run]
#
# What it does:
#   1. Reads the <!-- AUTO-GENERATED: base + modules[...] --> header from AGENTS.md
#   2. Re-fetches base.md + all listed modules from dev-standards (GitHub raw)
#   3. Replaces everything above "## Project-Specific" with fresh content
#   4. Leaves everything at and below "## Project-Specific" untouched
#   5. Syncs the .session/ scaffold next to AGENTS.md:
#        .session/_template.md          replaced if it differs (canonical copy)
#        .session/specs/adr/_template.md replaced if it differs (canonical copy)
#        .session/specs/adr/index.md    created only if missing (project data)
#        .session/archive/.gitkeep      created only if archive/ is missing
#      Session files themselves are never touched.
#
#   If a legacy claude.md is found instead of AGENTS.md (or claude.md's header
#   still names the old refresh-claude.sh script), this script migrates the
#   project automatically: claude.md -> AGENTS.md, plus a CLAUDE.md bridge
#   stub (`@AGENTS.md` import) for Claude Code. The '## Project-Specific'
#   section carries over byte-for-byte. Migration is idempotent — once a
#   project is migrated, later runs take the normal refresh path.
#
# Run from your project root, or pass --agents-md <path> explicitly.
# Set DEV_STANDARDS_RAW to fetch from elsewhere (e.g. file:///path/to/claude).
# =============================================================================

set -euo pipefail

# --- Defaults ----------------------------------------------------------------
AGENTS_MD="AGENTS.md"
DRY_RUN=false
DEV_STANDARDS_RAW_MAIN="https://raw.githubusercontent.com/pdrangeid/dev-standards/main/claude"
DEV_STANDARDS_RAW_DEV="https://raw.githubusercontent.com/pdrangeid/dev-standards/develop/claude"
DEV_STANDARDS_RAW="${DEV_STANDARDS_RAW:-$DEV_STANDARDS_RAW_DEV}"  # default to develop branch for latest updates
#DEV_STANDARDS_RAW="https://raw.githubusercontent.com/pdrangeid/dev-standards/main/claude"

# --- Flag parsing ------------------------------------------------------------
i=0
args=("$@")
while [ $i -lt ${#args[@]} ]; do
    case "${args[$i]}" in
        --agents-md)
            i=$((i+1))
            AGENTS_MD="${args[$i]}"
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
    esac
    i=$((i+1))
done

AGENTS_DIR="$(dirname "$AGENTS_MD")"
LEGACY_CLAUDE_MD="${AGENTS_DIR}/claude.md"
CLAUDE_MD_STUB="${AGENTS_DIR}/CLAUDE.md"
SESSION_DIR="${AGENTS_DIR}/.session"
ADR_DIR="${SESSION_DIR}/specs/adr"
ARCHIVE_DIR="${SESSION_DIR}/archive"

# --- Shared helpers ------------------------------------------------------------

# Fetch base.md + selected modules into $2, prefixed with a freshly-written
# header. Sets FETCH_FAILED=true on any failed fetch. Reads $SELECTED_MODULES.
fetch_fresh_content() {
    local modules_string="$1"
    local out_file="$2"

    cat > "$out_file" << AGENTSHEADER
<!-- AUTO-GENERATED: base + modules[${modules_string}] -->
<!-- Do not edit above ## Project-Specific — run refresh-dev-standards.sh to update -->
<!-- dev-standards: https://github.com/pdrangeid/dev-standards -->

AGENTSHEADER

    if curl -fsSL "${DEV_STANDARDS_RAW}/base.md" >> "$out_file" 2>/dev/null; then
        echo "  ✅ Fetched base.md"
    else
        echo "  ❌ Failed to fetch base.md from dev-standards from ${DEV_STANDARDS_RAW}"
        FETCH_FAILED=true
    fi

    local module
    for module in "${SELECTED_MODULES[@]}"; do
        module=$(echo "$module" | xargs)  # trim whitespace
        [ -z "$module" ] && continue
        if curl -fsSL "${DEV_STANDARDS_RAW}/modules/${module}.md" >> "$out_file" 2>/dev/null; then
            echo "  ✅ Fetched module: ${module}.md"
        else
            echo "  ⚠️  Could not fetch module: ${module}.md (check dev-standards repo)"
            FETCH_FAILED=true
        fi
    done
}

# Fetch the .session/ scaffold templates into directory $1.
# Sets FETCH_FAILED=true on any failed fetch.
fetch_session_templates() {
    local dir="$1" src
    for src in session-template.md adr-template.md adr-index-template.md; do
        if curl -fsSL "${DEV_STANDARDS_RAW}/${src}" -o "${dir}/${src}" 2>/dev/null; then
            echo "  ✅ Fetched ${src}"
        else
            echo "  ❌ Failed to fetch ${src} from ${DEV_STANDARDS_RAW}"
            FETCH_FAILED=true
        fi
    done
}

# Copy fetched template $1 to $2 if missing or different; $3 = "replace" or
# "create" (create never overwrites an existing file).
sync_file() {
    local src="$1" dest="$2" mode="$3"
    if [ -f "$dest" ]; then
        if [ "$mode" = create ] || cmp -s "$src" "$dest"; then
            echo "  ✔  $dest unchanged"
            return
        fi
        local verb="update"
    else
        local verb="create"
    fi
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] Would ${verb}: $dest"
    else
        mkdir -p "$(dirname "$dest")"
        cp "$src" "$dest"
        echo "  ✅ ${verb^}d $dest"
    fi
}

# Bring .session/ in line with the templates fetched into directory $1.
apply_session_scaffold() {
    local dir="$1"
    echo "Syncing .session/ scaffold..."
    sync_file "${dir}/session-template.md" "${SESSION_DIR}/_template.md" replace
    sync_file "${dir}/adr-template.md" "${ADR_DIR}/_template.md" replace
    sync_file "${dir}/adr-index-template.md" "${ADR_DIR}/index.md" create
    if [ -d "$ARCHIVE_DIR" ]; then
        echo "  ✔  $ARCHIVE_DIR/ exists"
    elif [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] Would create: $ARCHIVE_DIR/.gitkeep"
    else
        mkdir -p "$ARCHIVE_DIR"
        touch "$ARCHIVE_DIR/.gitkeep"
        echo "  ✅ Created $ARCHIVE_DIR/.gitkeep"
    fi
}

# True if $1 is exactly the generated CLAUDE.md stub: "@AGENTS.md", a blank
# line, then "## Claude Code" (anything after that is user content).
matches_known_stub_pattern() {
    local file="$1"
    [ "$(sed -n '1p' "$file")" = "@AGENTS.md" ] || return 1
    [ -z "$(sed -n '2p' "$file")" ] || return 1
    [ "$(sed -n '3p' "$file")" = "## Claude Code" ] || return 1
    return 0
}

# Create or refresh the CLAUDE.md bridge stub without clobbering unrecognized
# hand-authored content.
write_claude_stub() {
    if [ ! -f "$CLAUDE_MD_STUB" ]; then
        printf '@AGENTS.md\n\n## Claude Code\n' > "$CLAUDE_MD_STUB"
        echo "✅ $CLAUDE_MD_STUB stub created"
    elif matches_known_stub_pattern "$CLAUDE_MD_STUB"; then
        local tail_content
        tail_content=$(tail -n +3 "$CLAUDE_MD_STUB")
        { printf '@AGENTS.md\n\n'; printf '%s\n' "$tail_content"; } > "$CLAUDE_MD_STUB"
        echo "✅ $CLAUDE_MD_STUB verified (user additions below '## Claude Code' preserved)"
    else
        echo "⚠️  $CLAUDE_MD_STUB exists with unrecognized content — not touching it."
        echo "    Add '@AGENTS.md' manually at the top if you want Claude Code to use AGENTS.md."
    fi
}

# --- Legacy-state detection ---------------------------------------------------
legacy_state_detected() {
    [ -f "$LEGACY_CLAUDE_MD" ] || return 1
    [ -f "$AGENTS_MD" ] || return 0
    head -3 "$LEGACY_CLAUDE_MD" | grep -q "refresh-claude.sh" && return 0
    return 1
}

# --- Migration path ------------------------------------------------------------
run_migration() {
    echo "============================================="
    echo " refresh-dev-standards.sh — migrating claude.md -> AGENTS.md"
    echo "============================================="
    echo " Legacy file : $LEGACY_CLAUDE_MD"
    echo " New file    : $AGENTS_MD"
    [ "$DRY_RUN" = true ] && echo " Mode        : DRY RUN"
    echo "============================================="
    echo ""

    local legacy_header_line
    legacy_header_line=$(head -1 "$LEGACY_CLAUDE_MD")
    if [[ "$legacy_header_line" != "<!-- AUTO-GENERATED:"* ]]; then
        echo "❌ $LEGACY_CLAUDE_MD does not start with an AUTO-GENERATED comment."
        echo "   This file was not generated by setup-project.sh, or the header was removed."
        echo "   Cannot safely migrate — aborting."
        exit 1
    fi

    local modules_string
    modules_string=$(echo "$legacy_header_line" | sed -n 's/.*modules\[\([^]]*\)\].*/\1/p')
    SELECTED_MODULES=()
    if [ -n "$modules_string" ]; then
        IFS=',' read -ra SELECTED_MODULES <<< "$modules_string"
    fi

    local boundary_line
    boundary_line=$(grep -n "^## Project-Specific" "$LEGACY_CLAUDE_MD" | head -1 | cut -d: -f1)
    if [ -z "$boundary_line" ]; then
        echo "❌ Could not find '## Project-Specific' section in $LEGACY_CLAUDE_MD"
        echo "   Cannot safely split auto-generated vs. project-specific content."
        exit 1
    fi
    echo "📍 Project-Specific section starts at line $boundary_line"

    local project_specific
    project_specific=$(tail -n +"$boundary_line" "$LEGACY_CLAUDE_MD")

    FETCH_FAILED=false
    local tmp_file
    tmp_file=$(mktemp)
    echo "Fetching updated standards from dev-standards..."
    fetch_fresh_content "$modules_string" "$tmp_file"
    local tpl_dir
    tpl_dir=$(mktemp -d)
    fetch_session_templates "$tpl_dir"

    printf "\n---\n\n" >> "$tmp_file"
    echo "$project_specific" >> "$tmp_file"

    if [ "$FETCH_FAILED" = true ]; then
        echo ""
        echo "⚠️  One or more fetches failed. Review output above."
        echo "   The temp file has been written to: $tmp_file"
        echo "   Inspect it before applying manually. Migration aborted."
        exit 1
    fi

    if [ "$DRY_RUN" = true ]; then
        echo ""
        echo "  [DRY-RUN] Would write: $AGENTS_MD"
        echo "  [DRY-RUN] Would remove: $LEGACY_CLAUDE_MD"
        echo "  [DRY-RUN] Would create/update: $CLAUDE_MD_STUB"
        echo "  [DRY-RUN] New content preview (first 30 lines):"
        head -30 "$tmp_file" | sed 's/^/    /'
        rm -f "$tmp_file"
        echo ""
        apply_session_scaffold "$tpl_dir"
        rm -rf "$tpl_dir"
        echo ""
        echo "  [DRY-RUN] Migration complete — no files were written"
        echo ""
        return
    fi

    # Only remove claude.md after AGENTS.md is confirmed written.
    cp "$tmp_file" "$AGENTS_MD"
    rm -f "$tmp_file"
    echo "✅ $AGENTS_MD written"

    rm -f "$LEGACY_CLAUDE_MD"
    echo "✅ $LEGACY_CLAUDE_MD removed"

    write_claude_stub

    echo ""
    apply_session_scaffold "$tpl_dir"
    rm -rf "$tpl_dir"

    echo ""
    echo "✅ Migrated: claude.md -> AGENTS.md; CLAUDE.md created/updated (see above)"
    echo ""
}

# --- Normal refresh path --------------------------------------------------------
run_normal_refresh() {
    if [ ! -f "$AGENTS_MD" ]; then
        echo "❌ AGENTS.md not found at: $AGENTS_MD"
        echo "   Run from project root or pass --agents-md <path>"
        exit 1
    fi

    local header_line
    header_line=$(head -1 "$AGENTS_MD")
    if [[ "$header_line" != "<!-- AUTO-GENERATED:"* ]]; then
        echo "❌ $AGENTS_MD does not start with an AUTO-GENERATED comment."
        echo "   This file was not generated by setup-project.sh, or the header was removed."
        echo "   Cannot safely refresh — aborting."
        exit 1
    fi

    local modules_string
    modules_string=$(echo "$header_line" | sed -n 's/.*modules\[\([^]]*\)\].*/\1/p')

    echo "============================================="
    echo " refresh-dev-standards.sh"
    echo "============================================="
    echo " File    : $AGENTS_MD"
    echo " Modules : ${modules_string:-none}"
    [ "$DRY_RUN" = true ] && echo " Mode    : DRY RUN"
    echo "============================================="
    echo ""

    SELECTED_MODULES=()
    if [ -n "$modules_string" ]; then
        IFS=',' read -ra SELECTED_MODULES <<< "$modules_string"
    fi

    local boundary_line
    boundary_line=$(grep -n "^## Project-Specific" "$AGENTS_MD" | head -1 | cut -d: -f1)
    if [ -z "$boundary_line" ]; then
        echo "❌ Could not find '## Project-Specific' section in $AGENTS_MD"
        echo "   Cannot safely split auto-generated vs. project-specific content."
        exit 1
    fi
    echo "📍 Project-Specific section starts at line $boundary_line"

    local project_specific
    project_specific=$(tail -n +"$boundary_line" "$AGENTS_MD")

    FETCH_FAILED=false
    local tmp_file
    tmp_file=$(mktemp)
    echo "Fetching updated standards from dev-standards..."
    fetch_fresh_content "$modules_string" "$tmp_file"
    local tpl_dir
    tpl_dir=$(mktemp -d)
    fetch_session_templates "$tpl_dir"

    printf "\n---\n\n" >> "$tmp_file"
    echo "$project_specific" >> "$tmp_file"

    if [ "$FETCH_FAILED" = true ]; then
        echo ""
        echo "⚠️  One or more fetches failed. Review output above."
        echo "   The temp file has been written to: $tmp_file"
        echo "   Inspect it before applying manually."
        exit 1
    fi

    if [ "$DRY_RUN" = true ]; then
        echo ""
        echo "  [DRY-RUN] Would overwrite: $AGENTS_MD"
        echo "  [DRY-RUN] New content preview (first 30 lines):"
        head -30 "$tmp_file" | sed 's/^/    /'
        rm -f "$tmp_file"
    else
        cp "$tmp_file" "$AGENTS_MD"
        rm -f "$tmp_file"
        echo ""
        echo "✅ $AGENTS_MD refreshed."
        echo "   Auto-generated sections updated; ## Project-Specific preserved."
    fi
    echo ""
    apply_session_scaffold "$tpl_dir"
    rm -rf "$tpl_dir"
    echo ""
}

# --- Main ----------------------------------------------------------------------
if legacy_state_detected; then
    run_migration
else
    run_normal_refresh
fi
