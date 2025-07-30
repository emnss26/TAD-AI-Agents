using System;
using System.CodeDom.Compiler;
using System.IO;
using System.Linq;
using System.Web.Script.Serialization;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using Microsoft.CSharp;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitTemplateValidation
{
    // Clase actualizada para coincidir con la estructura de template_data.jsonl
    class Template
    {
        public string prompt_template { get; set; }
        public string completion_template { get; set; }
        public List<string> vars_needed { get; set; }
    }

    class Program
    {
        // Diccionario de valores "mock" para reemplazar las variables de las plantillas.
        static readonly Dictionary<string, string> MockData = new Dictionary<string, string>
        {
            // Nombres y Cadenas
            { "level_name", "\"Mock Level\"" },
            { "level_to_duplicate", "\"Mock Level\"" },
            { "original_level_name", "\"Mock Level 1\"" },
            { "new_level_name", "\"Mock Level 2\"" },
            { "wall_type_name", "\"Mock Wall Type\"" },
            { "original_name", "\"Original Name\"" },
            { "new_name", "\"New Name\"" },
            { "prefix", "\"PREFIX_\"" },
            { "family_name", "\"Mock Family\"" },
            { "room_name", "\"Mock Room\"" },
            { "view_name", "\"Mock View\"" },
            { "comment", "\"Mock Comment\"" },
            { "door_type_name", "\"Mock Door Type\"" },
            { "fire_rating", "\"60 min\"" },
            { "fire_rating_value", "\"60 min\"" },
            { "source_level", "\"Level 1\"" },
            { "target_level", "\"Level 2\"" },
            { "material_name", "\"Mock Material\"" },
            { "workset_name", "\"Mock Workset\"" },
            { "sheet_size", "\"A0\"" },
            { "template_name", "\"New Mock Template\"" },
            { "old_type_name", "\"Old Type Name\"" },
            { "new_type_name", "\"New Type Name\"" },
            { "mark_value", "\"M-01\"" },
            { "level1_name", "\"Level 1\"" },
            { "level2_name", "\"Level 2\"" },
            { "type_name_substring", "\"Generic\"" },
            { "parameter_name", "\"Comments\"" },
            { "parameter_value", "\"Mock Value\"" },
            { "text_to_find", "\"find_me\"" },
            { "new_text", "\"replace_me\"" },
            { "shape_name", "\"Mock Shape\"" },
            { "sheet_number", "\"A-101\"" },
            { "sheet_name", "\"Mock Sheet Name\"" },
            { "description", "\"Mock Description\"" },
            { "issued_by", "\"ML Engineer\"" },
            { "date", "\"2024-01-01\"" },
            { "buit_in_category_enum", "OST_Walls" }, // No necesita comillas, es un enum
            { "built_in_category_enum", "OST_Walls" }, // Corregido typo
            
            // Números (doubles)
            { "offset_m", "10.0" },
            { "elevation_m", "15.0" },
            { "thickness_mm", "150.0" },
            { "sill_height_mm", "900.0" },
            { "spacing_m", "5.0" },
            { "sill_height_m", "1.0" },
            { "height_m", "3.0" },
            { "thickness_cm", "20.0" },
            { "length_m", "10.0" },
            { "angle_degrees", "45.0" },
            { "width_m", "5.0" },
            { "slope_percentage", "5.0" },
            { "diameter_inch", "4.0" },
            { "width_mm", "300.0" },
            { "height_mm", "200.0" },
            { "text_size_mm", "2.5" },
            { "radius_m", "2.0" },
            { "distance_m", "10.0" },
            { "diameter_mm", "100.0" },
            { "value_m", "1.0" },
            { "size_m", "5.0" },

            // Números (enteros)
            { "num_worksets", "3" },
            { "rows", "5" },
            { "cols", "5" },
            { "num_horizontal", "4" },
            { "num_vertical", "6" },
            { "num_grids", "5" },
            { "color_r", "100" },
            { "color_g", "150" },
            { "color_b", "200" },
            { "transparency_percent", "50" },
            
            // Coordenadas
            { "x1", "0.0" }, { "y1", "0.0" }, { "z1", "0.0" },
            { "x2", "10.0" }, { "y2", "10.0" }, { "z2", "0.0" },
            { "eye_x_m", "50.0" }, { "eye_y_m", "-50.0" }, { "eye_z_m", "50.0" },
            { "p1x_m", "0.0" }, { "p1y_m", "0.0" }, { "p1z_m", "3.0" },
            { "p2x_m", "10.0" }, { "p2y_m", "0.0" }, { "p2z_m", "3.0" },
            { "start_x", "0.0" }, { "start_y", "0.0" }, { "start_z", "0.0" },
            { "end_x", "10.0" }, { "end_y", "10.0" }, { "end_z", "0.0" },
            { "coord_x", "5.0" }, { "coord_y", "5.0" },
            { "x_m", "5.0" }, { "y_m", "5.0" }, { "z_m", "3.0" },

            // Enums
            { "detail_level_enum", "\"Medium\"" }, // Se pasará como string para el Enum.Parse

            // Casos especiales (no necesitan valor, se manejan por nombre)
            { "coordinates", "" },
            { "single_point", "" },
            { "floor_size_m", "" },
            { "duct_size_mm", "" }
        };

        static void Main(string[] args)
        {
            if (args.Length < 3)
            {
                Console.WriteLine("Uso: CompilationValidator_Templates.exe <input_templates.jsonl> <success_templates.jsonl> <failed_templates.jsonl>");
                return;
            }

            string inputPath = args[0];
            string successPath = args[1];
            string failedPath = args[2];

            string revitApiPath = @"C:\Program Files\Autodesk\Revit 2025\RevitAPI.dll";
            string revitApiUIPath = @"C:\Program Files\Autodesk\Revit 2025\RevitAPIUI.dll";

            var serializer = new JavaScriptSerializer();
            using var wSucc = new StreamWriter(successPath);
            using var wFail = new StreamWriter(failedPath);

            foreach (var line in File.ReadLines(inputPath))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                Template template;
                try { template = serializer.Deserialize<Template>(line); }
                catch { continue; }

                // PASO 1: Generar código sintético (mocked)
                string mockedCode = GenerateMockedCode(template.completion_template, template.vars_needed, MockData);
                string wrappedCode = WrapInExecutorClass(mockedCode);

                var prov = new CSharpCodeProvider();
                var pars = new CompilerParameters
                {
                    GenerateExecutable = false,
                    GenerateInMemory = true
                };

                pars.ReferencedAssemblies.Add("System.dll");
                pars.ReferencedAssemblies.Add("System.Core.dll");
                pars.ReferencedAssemblies.Add("System.Web.Extensions.dll");
                pars.ReferencedAssemblies.Add(revitApiPath);
                pars.ReferencedAssemblies.Add(revitApiUIPath);
                
                var runtimeDir = RuntimeEnvironment.GetRuntimeDirectory();
                pars.ReferencedAssemblies.Add(Path.Combine(runtimeDir, "mscorlib.dll"));
                pars.ReferencedAssemblies.Add(Path.Combine(runtimeDir, "System.Runtime.dll"));

                // PASO 2: Compilar el código sintético
                var results = prov.CompileAssemblyFromSource(pars, wrappedCode);

                if (results.Errors.HasErrors)
                {
                    var errs = results.Errors
                                  .Cast<CompilerError>()
                                  .Select(e => $"{e.Line}:{e.ErrorNumber} {e.ErrorText}")
                                  .ToArray();
                    wFail.WriteLine(serializer.Serialize(new { prompt = template.prompt_template, completion = template.completion_template, errors = errs }));
                }
                else
                {
                    wSucc.WriteLine(line); // Escribir la línea original si tuvo éxito
                }
            }

            Console.WriteLine("✅ Validación de Plantillas completada.");
            Console.WriteLine($"  Éxitos:   {successPath}");
            Console.WriteLine($"  Fallidos: {failedPath}");
        }
        
        static string GenerateMockedCode(string templateCode, List<string> vars, Dictionary<string, string> mockData)
        {
            if (vars == null || !vars.Any())
            {
                return templateCode;
            }

            string currentCode = templateCode;
            foreach (var varName in vars)
            {
                if (mockData.ContainsKey(varName))
                {
                    // Reemplaza {variable} con su valor mock
                    currentCode = currentCode.Replace("{" + varName + "}", mockData[varName]);
                }
                else
                {
                    // Fallback para variables no definidas en el diccionario
                    currentCode = currentCode.Replace("{" + varName + "}", "\"UNMAPPED_VARIABLE\"");
                }
            }
            return currentCode;
        }

        static string WrapInExecutorClass(string rawCode)
        {
            rawCode = rawCode.Replace("UIDocument uidoc =", "UIDocument localUidoc =");
            rawCode = rawCode.Replace("uidoc.", "localUidoc.");

            var w = new StringWriter();
            w.WriteLine("using Autodesk.Revit.DB;");
            w.WriteLine("using Autodesk.Revit.DB.Structure;");
            w.WriteLine("using Autodesk.Revit.DB.Plumbing;");
            w.WriteLine("using Autodesk.Revit.DB.Electrical;");
            w.WriteLine("using Autodesk.Revit.DB.Mechanical;");
            w.WriteLine("using Autodesk.Revit.DB.Architecture;");
            w.WriteLine("using Autodesk.Revit.UI;");
            w.WriteLine("using Autodesk.Revit.UI.Selection;");
            w.WriteLine("using System;");
            w.WriteLine("using System.Collections.Generic;");
            w.WriteLine("using System.Linq;");
            w.WriteLine("using System.IO;"); // Añadido para Path y File
            w.WriteLine();
            w.WriteLine("namespace DynamicCode");
            w.WriteLine("{");
            w.WriteLine("    public class Executor");
            w.WriteLine("    {");
            w.WriteLine("        public void Run(UIDocument uidoc, Document doc)");
            w.WriteLine("        {");
            w.WriteLine("            UIDocument localUidoc = uidoc;"); // Declarar localUidoc para que esté disponible
            w.WriteLine("            // Código IA inyectado:");
            w.WriteLine(rawCode);
            w.WriteLine("        }");
            w.WriteLine("    }");
            w.WriteLine("}");
            return w.ToString();
        }
    }
}