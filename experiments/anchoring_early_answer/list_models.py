"""Print the Tinker models this key can sample, and tinker-cookbook's renderer for the ones named on the
command line (substring match). Used once to find the GLM-5.3-Flash id. Runs inside the Modal image."""
import sys

import tinker
from tinker_cookbook import model_info

caps = tinker.ServiceClient().get_server_capabilities()
names = [m.model_name for m in caps.supported_models]
for n in names:
    hit = any(s.lower() in n.lower() for s in sys.argv[1:])
    extra = ""
    if hit:
        try:
            extra = f"  renderers={list(model_info.get_recommended_renderer_names(n))}"
        except Exception as e:  # noqa: BLE001
            extra = f"  renderer lookup failed: {e}"
    print(("* " if hit else "  ") + n + extra)
