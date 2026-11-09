"""Print the Tinker models this key can sample (with context length where reported) and the cookbook's
recommended renderers for the ones matching the substrings given on the command line."""
import sys

import tinker
from tinker_cookbook import model_info

caps = tinker.ServiceClient().get_server_capabilities()
for m in caps.supported_models:
    n = m.model_name
    hit = any(s.lower() in n.lower() for s in sys.argv[1:] if s)
    extra = ""
    if hit:
        try:
            extra = f"  renderers={list(model_info.get_recommended_renderer_names(n.split(':')[0]))}"
        except Exception as e:  # noqa: BLE001
            extra = f"  renderer lookup failed: {e}"
    attrs = {k: v for k, v in vars(m).items() if k != "model_name"} if hasattr(m, "__dict__") else {}
    print(("* " if hit else "  ") + n + extra + (f"  {attrs}" if attrs else ""))
