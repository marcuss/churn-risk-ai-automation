#!/bin/zsh

set -e

echo "🚀 Setting up recurly-churn-risk repository..."

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

create_file_if_missing() {
  local file="$1"

  if [ ! -f "$file" ]; then
    touch "$file"
    echo "Created: $file"
  fi
}

move_if_exists() {
  local from="$1"
  local to="$2"

  if [ -f "$from" ] && [ ! -f "$to" ]; then
    mkdir -p "$(dirname "$to")"
    mv "$from" "$to"
    echo "Moved: $from → $to"
  fi
}

create_dir() {
  mkdir -p "$1"
}

# -----------------------------------------------------------------------------
# Directory structure
# -----------------------------------------------------------------------------

echo ""
echo "📁 Creating directories..."

create_dir app

create_dir src
create_dir src/ingestion
create_dir src/risk
create_dir src/ai
create_dir src/messaging
create_dir src/resilience

create_dir tests

create_dir docs
create_dir docs/adr
create_dir docs/screenshots
create_dir docs/diagrams

create_dir prompts
create_dir sample_data

# -----------------------------------------------------------------------------
# Move legacy files if they exist
# -----------------------------------------------------------------------------

echo ""
echo "📦 Moving legacy files..."

move_if_exists main.py app/main.py
move_if_exists sample_accounts.csv sample_data/sample_accounts.csv
move_if_exists prompt_design.md docs/prompt_design.md

# -----------------------------------------------------------------------------
# Root files
# -----------------------------------------------------------------------------

echo ""
echo "📄 Creating root files..."

create_file_if_missing README.md
create_file_if_missing CLAUDE.md
create_file_if_missing pyproject.toml
create_file_if_missing requirements.txt
create_file_if_missing .gitignore

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------

echo ""
echo "🐍 Creating app files..."

create_file_if_missing app/main.py

# -----------------------------------------------------------------------------
# Source files
# -----------------------------------------------------------------------------

create_file_if_missing src/config.py
create_file_if_missing src/models.py

create_file_if_missing src/ingestion/csv_loader.py

create_file_if_missing src/risk/risk_scoring.py
create_file_if_missing src/risk/risk_rules.py

create_file_if_missing src/ai/llm_client.py
create_file_if_missing src/ai/prompt_builder.py
create_file_if_missing src/ai/fallback_summary.py

create_file_if_missing src/messaging/slack_client.py
create_file_if_missing src/messaging/slack_formatter.py

create_file_if_missing src/resilience/retry.py
create_file_if_missing src/resilience/error_handler.py

# -----------------------------------------------------------------------------
# Python package markers
# -----------------------------------------------------------------------------

echo ""
echo "📦 Creating __init__.py files..."

create_file_if_missing src/__init__.py
create_file_if_missing src/ingestion/__init__.py
create_file_if_missing src/risk/__init__.py
create_file_if_missing src/ai/__init__.py
create_file_if_missing src/messaging/__init__.py
create_file_if_missing src/resilience/__init__.py

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

echo ""
echo "🧪 Creating tests..."

create_file_if_missing tests/test_risk_scoring.py
create_file_if_missing tests/test_fallback_summary.py
create_file_if_missing tests/test_slack_formatter.py

# -----------------------------------------------------------------------------
# Docs
# -----------------------------------------------------------------------------

echo ""
echo "📚 Creating documentation..."

create_file_if_missing docs/prompt_design.md
create_file_if_missing docs/risk_strategy.md
create_file_if_missing docs/sample_output.md

create_file_if_missing docs/adr/0001-deterministic-risk-scoring.md
create_file_if_missing docs/adr/0002-llm-only-for-summarization.md
create_file_if_missing docs/adr/0003-graceful-degradation.md
create_file_if_missing docs/adr/0004-slack-as-delivery-channel.md

create_file_if_missing docs/screenshots/.gitkeep
create_file_if_missing docs/diagrams/.gitkeep

# -----------------------------------------------------------------------------
# Prompt files
# -----------------------------------------------------------------------------

echo ""
echo "🤖 Creating prompt files..."

create_file_if_missing prompts/system_prompt.txt
create_file_if_missing prompts/risk_summary_prompt.txt
create_file_if_missing prompts/failed_generation_fallback.txt

# -----------------------------------------------------------------------------
# Sample data
# -----------------------------------------------------------------------------

echo ""
echo "📊 Creating sample data..."

create_file_if_missing sample_data/sample_accounts.csv

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

echo ""
echo "🧹 Cleaning old artifacts..."

if [ -f "recurly-churn-risk.iml" ]; then
  rm recurly-churn-risk.iml
  echo "Removed: recurly-churn-risk.iml"
fi

# -----------------------------------------------------------------------------
# Finished
# -----------------------------------------------------------------------------

echo ""
echo "✅ Repository setup complete."
echo ""

if command -v tree >/dev/null 2>&1; then
  tree .
else
  find . | sort
fi

