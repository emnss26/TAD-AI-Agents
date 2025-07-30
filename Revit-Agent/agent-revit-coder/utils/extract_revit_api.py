# pylance: reportMissingImports=false
import clr, inspect, json, os

# Apunta a tu DLL de Revit
dll_path = r"C:\Program Files\Autodesk\Revit 2025\RevitAPI.dll"
clr.AddReference(dll_path)
import Autodesk.Revit.DB as DB

api = []
for name, cls in inspect.getmembers(DB, inspect.isclass):
    # limitamos al namespace principal
    if cls.__module__ != "Autodesk.Revit.DB":
        continue

    # métodos públicos
    methods = []
    for mname, mobj in inspect.getmembers(cls, inspect.isfunction):
        sig = str(inspect.signature(mobj))
        methods.append({"name": mname, "signature": sig})

    # propiedades públicas
    props = []
    for pname, pobj in inspect.getmembers(cls, lambda o: isinstance(o, property)):
        props.append(pname)

    api.append({
        "type": name,
        "methods": methods,
        "properties": props
    })

out = os.path.join("data", "revit_api_reflection.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(api, f, indent=2)
print(f"✅ Dump completado en {out}")