#!/bin/bash
# Interactive CLI for LogSim with dataset discovery

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Paths
DATA_DIR="data/datasets"
COMPRESSED_DIR="evaluation/compressed"
RESULTS_DIR="evaluation/results"

# Global variables
declare -a datasets=()

# Scan datasets
scan_datasets() {
    echo -e "${BLUE}Scanning datasets...${NC}"
    datasets=()
    
    if [ ! -d "$DATA_DIR" ]; then
        echo -e "${RED}Error: $DATA_DIR not found!${NC}"
        return
    fi
    
    for dir in "$DATA_DIR"/*/ ; do
        if [ -d "$dir" ]; then
            name=$(basename "$dir")
            
            # Try multiple naming patterns
            log_file=""
            if [ -f "$dir/${name}_full.log" ]; then
                log_file="$dir/${name}_full.log"
            elif [ -f "$dir/${name}.log" ]; then
                log_file="$dir/${name}.log"
            elif [ -f "$dir/${name,,}.log" ]; then  # lowercase
                log_file="$dir/${name,,}.log"
            fi
            
            if [ -n "$log_file" ] && [ -f "$log_file" ]; then
                lines=$(wc -l < "$log_file" 2>/dev/null || echo "0")
                size=$(du -h "$log_file" 2>/dev/null | cut -f1 || echo "0")
                datasets+=("$name|$lines|$size|$log_file")
            fi
        fi
    done
}

# Main menu
show_main_menu() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}              ${CYAN}LogSim - Log Compression System${NC}                 ${PURPLE}║${NC}"
    echo -e "${PURPLE}║${NC}        ${YELLOW}Semantic-Aware Compression & Schema Extraction${NC}       ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Display datasets
    echo -e "${GREEN}📁 Detected Datasets (${#datasets[@]}):${NC}"
    if [ ${#datasets[@]} -eq 0 ]; then
        echo -e "  ${RED}No datasets found in $DATA_DIR${NC}"
    else
        i=1
        for dataset in "${datasets[@]}"; do
            IFS='|' read -r name lines size path <<< "$dataset"
            printf "  ${YELLOW}[%d]${NC} %-12s (%-10s lines, %s)\n" "$i" "$name" "$lines" "$size"
            ((i++))
        done
    fi
    echo ""
    
    # Actions
    echo -e "${GREEN}🎬 Actions:${NC}"
    echo -e "  ${YELLOW}[1]${NC} 🗜️  Compress selected datasets"
    echo -e "  ${YELLOW}[2]${NC} 🔍 Query compressed files"
    echo -e "  ${YELLOW}[3]${NC} 📊 Run full evaluation"
    echo -e "  ${YELLOW}[4]${NC} ⚖️  Benchmark comparison (vs gzip)"
    echo -e "  ${YELLOW}[5]${NC} 📈 View results"
    echo -e "  ${YELLOW}[6]${NC} ⚙️  Settings"
    echo -e "  ${YELLOW}[0]${NC} 🚪 Exit"
    echo ""
    
    read -p "Select option: " choice
    handle_main_menu "$choice"
}

# Handle main menu choice
handle_main_menu() {
    case "$1" in
        1)
            compress_datasets
            ;;
        2)
            query_files
            ;;
        3)
            run_evaluation
            ;;
        4)
            benchmark_comparison
            ;;
        5)
            view_results
            ;;
        6)
            settings_menu
            ;;
        0|x|X)
            echo -e "${YELLOW}Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option!${NC}"
            sleep 1
            ;;
    esac
}

# Compression flow
compress_datasets() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}                    ${CYAN}Compress Datasets${NC}                         ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [ ${#datasets[@]} -eq 0 ]; then
        echo -e "${RED}No datasets available!${NC}"
        read -p "Press enter to continue..."
        return
    fi
    
    # Dataset selection
    echo -e "${GREEN}📁 Select datasets to compress:${NC}"
    selected=()
    i=1
    for dataset in "${datasets[@]}"; do
        IFS='|' read -r name lines size path <<< "$dataset"
        read -p "  Include $name? [Y/n]: " include
        include=${include:-Y}
        if [[ "$include" =~ ^[Yy]$ ]]; then
            selected+=("$dataset")
            echo -e "  ${GREEN}✓${NC} $name selected"
        fi
        ((i++))
    done
    
    if [ ${#selected[@]} -eq 0 ]; then
        echo -e "${RED}No datasets selected!${NC}"
        read -p "Press enter to continue..."
        return
    fi
    
    echo ""
    echo -e "${YELLOW}⚙️  Compression Settings:${NC}"
    read -p "  Min support [3]: " min_support
    min_support=${min_support:-3}
    read -p "  Measure metrics? [Y/n]: " measure
    measure=${measure:-Y}
    
    echo ""
    echo -e "${CYAN}Starting compression...${NC}"
    
    mkdir -p "$COMPRESSED_DIR"
    
    for dataset in "${selected[@]}"; do
        IFS='|' read -r name lines size path <<< "$dataset"
        echo ""
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${CYAN}Compressing: $name${NC}"
        echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
        
        output="$COMPRESSED_DIR/${name,,}_full.lsc"
        
        if [[ "$measure" =~ ^[Yy]$ ]]; then
            python -m logsim compress -i "$path" -o "$output" --min-support "$min_support" -m
        else
            python -m logsim compress -i "$path" -o "$output" --min-support "$min_support"
        fi
    done
    
    echo ""
    echo -e "${GREEN}✓ Compression complete!${NC}"
    read -p "Press enter to continue..."
}

# Query files
query_files() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}                  ${CYAN}Query Compressed Logs${NC}                       ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [ ! -d "$COMPRESSED_DIR" ]; then
        echo -e "${RED}No compressed files found!${NC}"
        read -p "Press enter to continue..."
        return
    fi
    
    # List compressed files
    echo -e "${GREEN}📦 Available compressed files:${NC}"
    compressed_files=()
    i=1
    for file in "$COMPRESSED_DIR"/*.lsc; do
        if [ -f "$file" ]; then
            name=$(basename "$file" .lsc)
            size=$(du -h "$file" | cut -f1)
            compressed_files+=("$file")
            echo -e "  ${YELLOW}[$i]${NC} $name ($size)"
            ((i++))
        fi
    done
    
    if [ ${#compressed_files[@]} -eq 0 ]; then
        echo -e "${RED}No compressed files found!${NC}"
        read -p "Press enter to continue..."
        return
    fi
    
    echo ""
    read -p "Select file number (or 'b' for back): " selection
    
    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le "${#compressed_files[@]}" ]; then
        selected_file="${compressed_files[$((selection-1))]}"
        echo ""
        echo -e "${CYAN}Enter query (e.g., 'severity=ERROR'):${NC}"
        read -p "> " query
        
        if [ -n "$query" ]; then
            python -m logsim query -i "$selected_file" -q "$query"
        fi
    fi
    
    echo ""
    read -p "Press enter to continue..."
}

# Run evaluation
run_evaluation() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}                    ${CYAN}Run Full Evaluation${NC}                       ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${YELLOW}This will run comprehensive evaluation on all datasets.${NC}"
    echo -e "${YELLOW}This may take several minutes...${NC}"
    echo ""
    read -p "Continue? [Y/n]: " confirm
    confirm=${confirm:-Y}
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${CYAN}Running full evaluation...${NC}"
        cd evaluation
        python run_full_evaluation.py
        cd ..
        echo ""
        echo -e "${GREEN}✓ Evaluation complete!${NC}"
        echo -e "Results saved in ${RESULTS_DIR}/full_evaluation_results.md"
    fi
    
    echo ""
    read -p "Press enter to continue..."
}

# Benchmark comparison
benchmark_comparison() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}                ${CYAN}Benchmark vs gzip${NC}                           ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${YELLOW}This will compare LogSim compression with gzip.${NC}"
    echo ""
    read -p "Continue? [Y/n]: " confirm
    confirm=${confirm:-Y}
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${CYAN}Running benchmarks...${NC}"
        cd evaluation
        python run_query_benchmarks.py
        cd ..
        echo ""
        echo -e "${GREEN}✓ Benchmarks complete!${NC}"
    fi
    
    echo ""
    read -p "Press enter to continue..."
}

# View results
view_results() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}                    ${CYAN}View Results${NC}                              ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [ ! -d "$RESULTS_DIR" ]; then
        echo -e "${RED}No results found!${NC}"
        read -p "Press enter to continue..."
        return
    fi
    
    echo -e "${GREEN}📊 Available results:${NC}"
    echo -e "  ${YELLOW}[1]${NC} Full evaluation results"
    echo -e "  ${YELLOW}[2]${NC} Query performance"
    echo -e "  ${YELLOW}[3]${NC} Intrinsic metrics"
    echo -e "  ${YELLOW}[4]${NC} List all files"
    echo ""
    
    read -p "Select option: " choice
    
    case "$choice" in
        1)
            if [ -f "$RESULTS_DIR/full_evaluation_results.md" ]; then
                less "$RESULTS_DIR/full_evaluation_results.md"
            else
                echo -e "${RED}File not found!${NC}"
            fi
            ;;
        2)
            if [ -f "$RESULTS_DIR/query_performance.json" ]; then
                cat "$RESULTS_DIR/query_performance.json" | python -m json.tool | less
            else
                echo -e "${RED}File not found!${NC}"
            fi
            ;;
        3)
            echo -e "${CYAN}Intrinsic metrics files:${NC}"
            ls -lh "$RESULTS_DIR"/intrinsic_*.json 2>/dev/null || echo -e "${RED}No intrinsic metrics found${NC}"
            ;;
        4)
            ls -lh "$RESULTS_DIR"
            ;;
        *)
            echo -e "${RED}Invalid option!${NC}"
            ;;
    esac
    
    echo ""
    read -p "Press enter to continue..."
}

# Settings menu
settings_menu() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}                ${CYAN}Settings & Configuration${NC}                    ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${GREEN}📂 Paths:${NC}"
    echo -e "  Datasets:    ${CYAN}$DATA_DIR${NC}"
    echo -e "  Compressed:  ${CYAN}$COMPRESSED_DIR${NC}"
    echo -e "  Results:     ${CYAN}$RESULTS_DIR${NC}"
    echo ""
    
    echo -e "${GREEN}🛠️  Default Settings:${NC}"
    echo -e "  Min support:  ${CYAN}3${NC}"
    echo -e "  Measure:      ${CYAN}Yes${NC}"
    echo ""
    
    echo -e "${GREEN}ℹ️  System Info:${NC}"
    echo -e "  Python:       ${CYAN}$(python --version 2>&1)${NC}"
    echo -e "  LogSim:       ${CYAN}$(python -m logsim --version 2>&1)${NC}"
    echo -e "  Working dir:  ${CYAN}$(pwd)${NC}"
    echo ""
    
    read -p "Press enter to continue..."
}

# Main execution
main() {
    # Check if running in Docker
    if [ -f /.dockerenv ]; then
        echo -e "${CYAN}🐳 Running in Docker container${NC}"
        sleep 1
    fi
    
    # Scan datasets on startup
    scan_datasets
    
    # Show main menu
    while true; do
        show_main_menu
    done
}

main "$@"
