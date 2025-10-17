import glob, yaml, types, pytest
from src.plugins.base import registry

def load_yaml_cases():
    for path in glob.glob("tests/cases/*.yaml"):
        with open(path, "r", encoding="utf-8") as f:
            yield path, yaml.safe_load(f)

@pytest.mark.parametrize("path, spec", list(load_yaml_cases()))
def test_plugin_yaml_cases(path, spec):
    plugin_id = spec["plugin"]
    plugin = registry[plugin_id]()
    Params = plugin.ParamsModel
    ctx_dict = spec.get("context", {})
    ctx = types.SimpleNamespace(**ctx_dict)

    for case in spec["cases"]:
        params = Params(**case["params"]).model_dump()
        res = plugin.run(ctx, **params)
        exp = case["expect"]
        assert res.passed == exp["passed"], f"{path}:{case['name']}"
        if "message_contains" in exp:
            assert exp["message_contains"] in (res.message or "")
