#!/bin/bash
# start.sh - Startup script for Model Manager

set -e

echo "🚀 Starting Model Manager service..."

# Create directories if they don't exist
mkdir -p models downloads logs

# Check if .env exists, create from template if not
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.template .env
    echo "⚠️  Please edit .env with your configuration before running again"
    exit 1
fi

# Install dependencies if virtual environment doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Run database migrations or setup if needed
echo "🔧 Running setup tasks..."
python -c "from ai_core.config.settings import validate_directories; validate_directories()"

# Start the server
echo "✅ Starting FastAPI server..."
python -m uvicorn ai_core.main:app --host 0.0.0.0 --port 8000 --reload
