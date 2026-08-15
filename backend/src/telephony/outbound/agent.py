import importlib.util
import os
import sys

# Load main agent module from src/agent.py directly
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
main_agent_path = os.path.join(src_dir, "agent.py")

spec = importlib.util.spec_from_file_location("main_agent", main_agent_path)
main_agent = importlib.util.module_from_spec(spec)
sys.modules["main_agent"] = main_agent
spec.loader.exec_module(main_agent)

if __name__ == "__main__":
    main_agent.cli.run_app(main_agent.server)
