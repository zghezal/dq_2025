from pydantic import BaseModel
from src.plugins.base import registry, Result

def test_registry_not_empty():
    assert len(registry) > 0

def test_each_plugin_respects_contract():
    for pid, Plugin in registry.items():
        assert getattr(Plugin, "plugin_id") == pid
        assert getattr(Plugin, "label")
        assert getattr(Plugin, "group")

        Params = getattr(Plugin, "ParamsModel", None)
        assert Params and issubclass(Params, BaseModel), f"{pid}: ParamsModel manquant"

        # Build generic sample params from model fields
        sample = {}
        for name, fld in Params.model_fields.items():
            ann = fld.annotation
            if hasattr(ann, "model_fields"):  # nested submodel: fill recursively with simple defaults
                sub = {}
                for n2, f2 in ann.model_fields.items():
                    a2 = f2.annotation
                    if a2 in (int, float): sub[n2] = 0
                    elif a2 is bool: sub[n2] = True
                    else: sub[n2] = "x"
                sample[name] = sub
            else:
                if ann in (int, float): sample[name] = 0
                elif ann is bool: sample[name] = True
                else: sample[name] = "x"

        class Ctx: pass
        Ctx.metrics_values = {"x": 0}

        res = Plugin().run(Ctx, **Params(**sample).model_dump())
        assert isinstance(res, Result)
        assert isinstance(res.passed, bool)
        assert hasattr(res, "message")
