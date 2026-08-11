import asyncio
import importlib.util
import os
import sys

src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
main_dial_path = os.path.join(src_dir, "dial.py")

spec = importlib.util.spec_from_file_location("main_dial", main_dial_path)
main_dial = importlib.util.module_from_spec(spec)
sys.modules["main_dial"] = main_dial
spec.loader.exec_module(main_dial)

if __name__ == "__main__":
    target_user = sys.argv[1] if len(sys.argv) > 1 else "ramesh_01"
    target_dest = sys.argv[2] if len(sys.argv) > 2 else main_dial.SIP_DESTINATION
    asyncio.run(main_dial.make_outbound_call(target_user, target_dest))
