#!/bin/bash
set -e

echo "🔧 Setting up environment..."

# Ensure Pixi is in the PATH and properly installed
if ! command -v pixi &> /dev/null; then
    echo "Installing Pixi..."
    curl -fsSL https://pixi.sh/install.sh | bash
    export PATH="$HOME/.pixi/bin:$PATH"
    echo 'export PATH="$HOME/.pixi/bin:$PATH"' >> ~/.bashrc
    echo 'export PATH="$HOME/.pixi/bin:$PATH"' >> ~/.profile
fi

# Verify Pixi installation
echo "✅ Pixi version: $(pixi --version)"

# Install Python packages if needed
pip install --upgrade pip
pip install black pylint

# Initialize pixi project if pixi.toml doesn't exist
if [ ! -f "pixi.toml" ]; then
    echo "Initializing Pixi project..."
    pixi init --name ehs-agent-kg
fi

echo "🚀 Environment setup complete!"