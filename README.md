
# System Requirements
The InfoBlueprint data profiling tool requires uv to manage python dependencies and can be installed using the following command:

#### Mac/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows:
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Once uv is installed, run the following commands to launch the  profiling tool:

```bash
uv init
uv add -r requirements.txt
source .venv/bin/activate
streamlit run 01_connector.py
```