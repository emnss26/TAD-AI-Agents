import yaml
import re
import json
import textwrap
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

class RevitAgent:
    def __init__(self, cfg_path="src/config.yaml"):
        cfg = yaml.safe_load(open(cfg_path, "r"))

        # Inicializa tokenizer y modelo con LoRA adapter
        self.tokenizer = AutoTokenizer.from_pretrained(cfg["model_name"])
        self.tokenizer.add_special_tokens({'additional_special_tokens': ['<CLS>', '<END>']})
        self.tokenizer.pad_token = self.tokenizer.eos_token

        base = AutoModelForCausalLM.from_pretrained(
            cfg["model_name"],
            load_in_8bit=True,
            device_map="auto"
        )
        base.resize_token_embeddings(len(self.tokenizer))
        self.model = PeftModel.from_pretrained(base, cfg["lora_path"]).to("cuda")
        self.model.eval()

    def classify_element(self, prompt: str) -> str:
        """
        Clasifica el tipo de elemento según la instrucción.
        Retorna exactamente: Wall, Floor, Column, Beam o Ceiling.
        """
        examples = [
            ("Crea un muro en Nivel 1 de (0,0,0) a (5,0,0) alto 5m.", "Wall"),
            ("Genera un piso rectangular de 10x8m.", "Floor"),
            ("Inserta una columna en X=10,Y=5.", "Column"),
            ("Crea una viga entre dos columnas.", "Beam"),
            ("Modela un plafón a 2.8m sobre el nivel.", "Ceiling")
        ]
        cls_prompt = "<CLS> Clasifica con una palabra (Wall, Floor, Column, Beam, Ceiling):\n"
        for text, label in examples:
            cls_prompt += f"Ejemplo: {text} → {label}\n"
        cls_prompt += f"Instrucción: {prompt} →"

        inputs = self.tokenizer(cls_prompt, return_tensors="pt", padding=True, truncation=True).to("cuda")
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=3,
            do_sample=False,
            num_beams=1,
            pad_token_id=self.tokenizer.eos_token_id
        )
        gen = outputs[0][inputs.input_ids.shape[-1]:]
        raw = self.tokenizer.decode(gen, skip_special_tokens=True)
        return raw.strip().split()[0]

    def generate_code(self, prompt: str, convo_id: str = None) -> str:
        # 1) Clasificar tipo
        element = self.classify_element(prompt)

        # 2) Extraer coordenadas y altura sin confundir "Nivel 1"
        coord_matches = re.findall(r"\(\s*([0-9\.]+)\s*,\s*([0-9\.]+)\s*,\s*([0-9\.]+)\s*\)", prompt)
        if len(coord_matches) >= 2:
            (x1, y1, z1), (x2, y2, z2) = [tuple(map(float, m)) for m in coord_matches[:2]]
        else:
            x1 = y1 = z1 = x2 = y2 = z2 = 0.0
        h_match = re.search(r"alto\s*([0-9\.]+)", prompt, re.IGNORECASE)
        h = float(h_match.group(1)) if h_match else 0.0

        # 3) Plantillas fijas
        if element == "Wall":
            body = textwrap.dedent(f"""
                var level = new FilteredElementCollector(doc)
                    .OfClass(typeof(Level))
                    .WhereElementIsNotElementType()
                    .FirstOrDefault(l => l.Name == "Level 1");
                var wallType = new FilteredElementCollector(doc)
                    .OfCategory(BuiltInCategory.OST_Walls)
                    .WhereElementIsElementType()
                    .Cast<WallType>()
                    .First();
                var line = Line.CreateBound(new XYZ({x1},{y1},{z1}), new XYZ({x2},{y2},{z2}));
                Wall.Create(doc, line, wallType.Id, level.Id, {h}, 0.0, false, false);
            """)
        elif element == "Floor":
            nums = list(map(float, re.findall(r"([0-9]+\.?[0-9]*)x([0-9]+\.?[0-9]*)", prompt)))
            w, d = nums[0] if nums else (0.0, 0.0)
            body = textwrap.dedent(f"""
                var level = new FilteredElementCollector(doc)
                    .OfClass(typeof(Level))
                    .WhereElementIsNotElementType()
                    .FirstOrDefault(l => l.Name == "Level 1");
                var floorType = new FilteredElementCollector(doc)
                    .OfClass(typeof(FloorType))
                    .First();
                CurveLoop loop = new CurveLoop();
                loop.Append(Line.CreateBound(new XYZ(0,0,0), new XYZ({w},0,0)));
                loop.Append(Line.CreateBound(new XYZ({w},0,0), new XYZ({w},{d},0)));
                loop.Append(Line.CreateBound(new XYZ({w},{d},0), new XYZ(0,{d},0)));
                loop.Append(Line.CreateBound(new XYZ(0,{d},0), new XYZ(0,0,0)));
                Floor.Create(doc, new List<CurveLoop>{{loop}}, floorType.Id, level.Id);
            """)
        elif element == "Column":
            nums = list(map(float, re.findall(r"X\s*=\s*([0-9\.]+)\s*,?\s*Y\s*=\s*([0-9\.]+)", prompt)))
            x, y = nums[0] if nums else (0.0, 0.0)
            body = textwrap.dedent(f"""
                var level = new FilteredElementCollector(doc)
                    .OfClass(typeof(Level))
                    .WhereElementIsNotElementType()
                    .FirstOrDefault(l => l.Name == "Level 1");
                var colSym = new FilteredElementCollector(doc)
                    .OfCategory(BuiltInCategory.OST_StructuralColumns)
                    .WhereElementIsElementType()
                    .Cast<FamilySymbol>()
                    .First();
                if (!colSym.IsActive) colSym.Activate();
                doc.Regenerate();
                doc.Create.NewFamilyInstance(new XYZ({x},{y},0), colSym, level, StructuralType.Column);
            """)
        else:
            body = f"// Elemento '{element}' no soportado aún."

        # 4) Envolver en transacción
        wrapped = textwrap.indent(body, '    ')
        return textwrap.dedent(f"""
            using (Transaction tx = new Transaction(doc, "AIAction"))
            {{
                tx.Start();
            {{wrapped}}
                tx.Commit();
            }}
            doc.Regenerate();
        """ )

# Test rápido
if __name__ == "__main__":
    agent = RevitAgent("src/config.yaml")
    print(agent.generate_code("Crea un muro en Nivel 1 de (0,0,0) a (5,0,0) alto 5m."))