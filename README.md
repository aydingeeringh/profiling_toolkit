# InfoBlueprint Data Profiling Tool

## Overview
InfoBlueprint is a powerful data profiling tool that helps you analyze and understand your datasets through an interactive web interface. Built with Streamlit, it provides comprehensive insights into your data structure, quality, and patterns.

## Features
- Interactive data exploration
- Automated data profiling and statistics
- Pattern recognition
- Visualization capabilities
- Support for multiple data sources

## System Requirements

### Prerequisites
- Python 3.8 or higher
- uv package manager

## Installation

### 1. Install uv Package Manager

#### Mac/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows:
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Setup Project Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/infoblueprint.git
cd infoblueprint

# Initialize virtual environment and install dependencies
uv init
uv add -r requirements.txt
```

### 3. Activate Virtual Environment

#### Mac/Linux:
```bash
source .venv/bin/activate
```

#### Windows:
```bash
.venv\Scripts\activate
```

### 4. Launch Application
```bash
streamlit run 01_connector.py
```

## Usage
1. Open your web browser and navigate to `http://localhost:8501`
2. Upload your dataset through the web interface
3. Configure profiling parameters
4. Explore the generated insights and visualizations

## Troubleshooting

### Common Issues
1. **Installation Fails**
   - Ensure Python version compatibility
   - Check system requirements
   - Verify internet connection

2. **Application Won't Start**
   - Confirm virtual environment is activated
   - Check port 8501 availability
   - Verify dependencies installation

3. **Memory Issues**
   - Increase available RAM
   - Reduce dataset size