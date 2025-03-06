#!/bin/bash
# GhostForge Virtual Environment Setup
# This script creates a virtual environment and helps set up automatic activation

# Colors for pretty output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== GhostForge Virtual Environment Setup ===${NC}\n"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python -m venv .venv
    CREATED_NEW=true
else
    echo -e "${GREEN}Virtual environment already exists.${NC}"
    CREATED_NEW=false
fi

# Activate the virtual environment for this script
source .venv/bin/activate

# Install required packages
if [ "$CREATED_NEW" = true ] || [ "$1" == "--force" ]; then
    echo -e "\n${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt
fi

# Create .envrc file for direnv if it doesn't exist
if [ ! -f ".envrc" ]; then
    echo -e "\n${YELLOW}Creating .envrc file for direnv...${NC}"
    echo 'source .venv/bin/activate' > .envrc
    
    # Check if direnv is installed
    if command -v direnv &> /dev/null; then
        echo -e "${GREEN}direnv is installed. Running direnv allow...${NC}"
        direnv allow
    else
        echo -e "${YELLOW}direnv is not installed. To enable automatic venv activation:${NC}"
        echo -e "1. Install direnv: ${BLUE}brew install direnv${NC} (on macOS)"
        echo -e "2. Add to your shell (~/.bashrc, ~/.zshrc, etc.):"
        echo -e "   ${BLUE}eval \"\$(direnv hook bash)\"${NC} or ${BLUE}eval \"\$(direnv hook zsh)\"${NC}"
        echo -e "3. Then run: ${BLUE}direnv allow${NC} in this directory"
    fi
fi

# Create a simple activation script for manual use
echo -e "\n${YELLOW}Creating activation script...${NC}"
cat > activate_ghostforge.sh << 'EOF'
#!/bin/bash
# Activate GhostForge virtual environment
source .venv/bin/activate
echo "GhostForge virtual environment activated. Run 'deactivate' to exit."
EOF
chmod +x activate_ghostforge.sh

# Summary and instructions
echo -e "\n${GREEN}Setup complete!${NC}"
echo -e "\n${BLUE}To manually activate the virtual environment:${NC}"
echo -e "  source .venv/bin/activate"
echo -e "  or"
echo -e "  ./activate_ghostforge.sh"

echo -e "\n${BLUE}To run GhostForge:${NC}"
echo -e "  python -m ghostforge.shell"

echo -e "\n${BLUE}To set up the model:${NC}"
echo -e "  python tinyfs_auto_download.py"

# If direnv is not detected, remind about automatic activation
if ! command -v direnv &> /dev/null; then
    echo -e "\n${YELLOW}For automatic environment activation when entering this directory:${NC}"
    echo -e "Install direnv (https://direnv.net/) and add it to your shell configuration."
fi 