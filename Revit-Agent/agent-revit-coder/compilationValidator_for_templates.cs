using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;
using System.CodeDom.Compiler;
using System.Web.Script.Serialization;
using System.Runtime.InteropServices;
using Microsoft.CSharp;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitApiValidation
{
    class Template
    {
        public string prompt_template { get; set; }
        public string completion_template { get; set; }
        public List<string> vars_needed { get; set; }
    }

    class Program
    {
        // Mapeo de enums comunes a literales válidos de la API
        static readonly Dictionary<string, string> EnumMapping = new Dictionary<string, string>
        {
            { "detail_level_enum", "ViewDetailLevel.Fine" },
            { "built_in_category_enum", "BuiltInCategory.OST_Walls" },
            { "ifc_version_enum", "IFCVersion.IFC2x3" }
        };

        static void Main(string[] args)
        {
            if (args.Length < 3)
            {
                Console.WriteLine("Uso: TemplateValidator.exe <input.jsonl> <success.jsonl> <failed.jsonl> [<cleaned_success.jsonl> <cleaned_failed_full.jsonl>]");
                return;
            }

            string inputPath = args[0];
            string successPath = args[1];
            string failedPath = args[2];

            string cleanSuccPath = args.Length >= 4
                ? args[3]
                : Path.Combine(Path.GetDirectoryName(successPath) ?? string.Empty,
                    Path.GetFileNameWithoutExtension(successPath) + ".cleaned" + Path.GetExtension(successPath));
            string cleanFailedFull = args.Length >= 5
                ? args[4]
                : Path.Combine(Path.GetDirectoryName(failedPath) ?? string.Empty,
                    Path.GetFileNameWithoutExtension(failedPath) + ".full" + Path.GetExtension(failedPath));

            string revitApiPath = @"C:\Program Files\Autodesk\Revit 2025\RevitAPI.dll";
            string revitApiUIPath = @"C:\Program Files\Autodesk\Revit 2025\RevitAPIUI.dll";

            var serializer = new JavaScriptSerializer();
            using var wSucc = new StreamWriter(successPath);
            using var wFail = new StreamWriter(failedPath);
            using var wCleanSucc = new StreamWriter(cleanSuccPath);
            using var wCleanFail = new StreamWriter(cleanFailedFull);

            foreach (var line in File.ReadLines(inputPath))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                Template tpl;
                try { tpl = serializer.Deserialize<Template>(line); }
                catch { continue; }
                if (tpl == null || string.IsNullOrWhiteSpace(tpl.completion_template)) continue;

                // Genera código saneado con mocks y ajustes automáticos
                string mockedCode = GenerateMockedCode(tpl.completion_template, tpl.vars_needed);
                string wrapped = WrapInExecutorClass(mockedCode);

                var prov = new CSharpCodeProvider();
                var pars = new CompilerParameters { GenerateInMemory = true };

                // Ensamblados .NET necesarios
                pars.ReferencedAssemblies.Add("System.dll");
                pars.ReferencedAssemblies.Add("System.Core.dll");
                pars.ReferencedAssemblies.Add("System.Linq.dll");
                pars.ReferencedAssemblies.Add("System.Web.Extensions.dll");

                // Ensamblados Revit
                pars.ReferencedAssemblies.Add(revitApiPath);
                pars.ReferencedAssemblies.Add(revitApiUIPath);

                var runtimeDir = RuntimeEnvironment.GetRuntimeDirectory();
                pars.ReferencedAssemblies.Add(Path.Combine(runtimeDir, "mscorlib.dll"));
                pars.ReferencedAssemblies.Add(Path.Combine(runtimeDir, "System.Runtime.dll"));

                var results = prov.CompileAssemblyFromSource(pars, wrapped);

                if (results.Errors.HasErrors)
                {
                    var errs = results.Errors.Cast<CompilerError>()
                        .Select(e => $"{e.Line}:{e.ErrorNumber} {e.ErrorText}")
                        .ToArray();
                    wFail.WriteLine(serializer.Serialize(new { prompt = tpl.prompt_template, errors = errs }));
                    wCleanFail.WriteLine(serializer.Serialize(new { prompt = tpl.prompt_template, completion = tpl.completion_template, errors = errs }));
                }
                else
                {
                    wSucc.WriteLine(serializer.Serialize(new { prompt = tpl.prompt_template, completion = tpl.completion_template }));
                    wCleanSucc.WriteLine(serializer.Serialize(new { prompt = tpl.prompt_template, completion = tpl.completion_template }));
                }
            }

            Console.WriteLine("✅ Validación completada.");
        }

        static string GenerateMockedCode(string templateCode, List<string> vars)
        {
            if (string.IsNullOrEmpty(templateCode))
                return string.Empty;

            // Eliminar interpolaciones C# para evitar '$"...{var}...'"
            templateCode = Regex.Replace(templateCode, @"\$@?\""", "\"");

            var sb = new StringBuilder();
            string code = templateCode;

            if (vars != null)
            {
                foreach (var name in vars.Distinct())
                {
                    // Enum mapeados a literales reales, inline sin var
                    if (EnumMapping.TryGetValue(name, out var enumVal))
                    {
                        code = code.Replace("{" + name + "}", enumVal);
                        continue;
                    }

                    string decl;
                    var low = name.ToLowerInvariant();

                    // Prefix como string
                    if (low == "prefix")
                    {
                        decl = $"var {name} = \"{name}_\";";
                    }
                    // Bytes para colores RGB
                    else if (low.EndsWith("_r") || low.EndsWith("_g") || low.EndsWith("_b"))
                    {
                        decl = $"var {name} = (byte)1;";
                    }
                    // Porcentajes como int
                    else if (low.Contains("percent"))
                    {
                        decl = $"var {name} = 1;";
                    }
                    // Conteos como int
                    else if (low.StartsWith("num_") || low == "rows" || low == "cols")
                    {
                        decl = $"var {name} = 1;";
                    }
                    // Strings y nombres
                    else if (low.Contains("name") || low.Contains("comment") || low.Contains("material") || low.Contains("family") || low.Contains("type"))
                    {
                        decl = $"var {name} = \"Mock_{name}\";";
                    }
                    // Por defecto double
                    else
                    {
                        decl = $"var {name} = 1.0;";
                    }

                    sb.AppendLine(decl);
                    code = code.Replace("{" + name + "}", name);
                }
            }

            // Ajustar FilteredElementCollector para soportar LINQ
            code = Regex.Replace(code,
                @"\.OfClass\(typeof\((\w+)\)\)",
                ".OfClass(typeof($1)).Cast<$1>()",
                RegexOptions.IgnoreCase);

            // Fallback para cualquier placeholder restante
            code = Regex.Replace(code, @"\{\w+\}", "1.0");

            sb.AppendLine();
            sb.AppendLine(code);
            return sb.ToString();
        }

        static string WrapInExecutorClass(string rawCode)
        {
            if (string.IsNullOrEmpty(rawCode))
                return rawCode;

            // Evitar redeclaraciones de uidoc
            rawCode = Regex.Replace(rawCode, @"UIDocument\s+uidoc\s*=.*?;", "// uidoc proporcionado");

            var sb = new StringBuilder();
            sb.AppendLine("using System;");
            sb.AppendLine("using System.Linq;");
            sb.AppendLine("using System.Collections.Generic;");
            sb.AppendLine("using System.Text;");
            sb.AppendLine("using Autodesk.Revit.DB;");
            sb.AppendLine("using Autodesk.Revit.DB.Structure;");
            sb.AppendLine("using Autodesk.Revit.DB.Plumbing;");
            sb.AppendLine("using Autodesk.Revit.DB.Electrical;");
            sb.AppendLine("using Autodesk.Revit.DB.Mechanical;");
            sb.AppendLine("using Autodesk.Revit.DB.Architecture;");
            sb.AppendLine("using Autodesk.Revit.UI;");
            sb.AppendLine("using Autodesk.Revit.UI.Selection;");
            sb.AppendLine();
            sb.AppendLine("namespace DynamicCode");
            sb.AppendLine("{");
            sb.AppendLine("    public class Executor");
            sb.AppendLine("    {");
            sb.AppendLine("        public void Run(UIDocument uidoc, Document doc)");
            sb.AppendLine("        {");
            sb.AppendLine(rawCode);
            sb.AppendLine("            using (Transaction t = new Transaction(doc, \"Regenerate\")) { t.Start(); doc.Regenerate(); t.Commit(); }");
            sb.AppendLine("        }");
            sb.AppendLine("    }");
            sb.AppendLine("}");
            return sb.ToString();
        }
    }
}