#!/usr/bin/env bash
# CareerAI Pro — One-Command Setup
set -e
GREEN='\033[0;32m'; GOLD='\033[0;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
echo -e "\n${GOLD}╔══════════════════════════════════════════════╗"
echo -e "║      CareerAI Pro — Setup & Installation     ║"
echo -e "╚══════════════════════════════════════════════╝${NC}\n"
echo -e "${BLUE}[1/4] Checking Python...${NC}"
python3 --version &>/dev/null || { echo -e "${RED}Python 3 not found. Install from python.org${NC}"; exit 1; }
echo -e "${GREEN}✓ $(python3 --version)${NC}"
echo -e "${BLUE}[2/4] Creating virtual environment...${NC}"
python3 -m venv venv
[[ "$OSTYPE" == msys* || "$OSTYPE" == win32 ]] && source venv/Scripts/activate || source venv/bin/activate
echo -e "${GREEN}✓ venv created${NC}"
echo -e "${BLUE}[3/4] Installing dependencies...${NC}"
pip install --upgrade pip -q && pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo -e "${BLUE}[4/4] Training ML model (75-80%+ accuracy)...${NC}"
python ml/train_model.py
echo -e "\n${GOLD}╔══════════════════════════════════════════════╗"
echo -e "║          ✅  Setup Complete!                 ║"
echo -e "╚══════════════════════════════════════════════╝${NC}\n"
echo -e "  Start the server:"
[[ "$OSTYPE" == msys* || "$OSTYPE" == win32 ]] && echo -e "  ${GOLD}venv\\Scripts\\activate${NC}" || echo -e "  ${GOLD}source venv/bin/activate${NC}"
echo -e "  ${GOLD}python backend/server.py${NC}\n"
echo -e "  Open: ${GOLD}http://localhost:8000${NC}"
echo -e "  Add Groq API key in the sidebar for AI features.\n"
