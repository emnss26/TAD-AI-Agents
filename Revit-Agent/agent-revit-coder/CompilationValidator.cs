using System;
using System.CodeDom.Compiler;
using System.IO;
using System.Linq;
using System.Web.Script.Serialization;
using System.Runtime.InteropServices;
using System.Reflection;
using System.Text.RegularExpressions;
using Microsoft.CSharp;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitApiValidation
{
    class Example
    {
        public string prompt     { get; set; }
        public string completion { get; set; }
    }

    class Program
    {
        static void Main(string[] args)
        {
            if (args.Length < 5)
            {
                Console.WriteLine("Uso: CompilationValidator.exe <input.jsonl> <success.jsonl> <failed.jsonl> <cleaned_success.jsonl> <cleaned_failed_full.jsonl>");
                return;
            }

            string inputPath        = args[0];
            string successPath      = args[1];
            string failedPath       = args[2];
            string cleanSuccPath    = args[3];
            string cleanFailedFull  = args[4];

            string revitApiPath     = @"C:\Program Files\Autodesk\Revit 2025\RevitAPI.dll";
            string revitApiUIPath   = @"C:\Program Files\Autodesk\Revit 2025\RevitAPIUI.dll";

            var serializer = new JavaScriptSerializer();
            using var wSucc      = new StreamWriter(successPath);
            using var wFail      = new StreamWriter(failedPath);
            using var wCleanSucc = new StreamWriter(cleanSuccPath);
            using var wCleanFail = new StreamWriter(cleanFailedFull);

            foreach (var line in File.ReadLines(inputPath))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                Example ex;
                try { ex = serializer.Deserialize<Example>(line); }
                catch { continue; }

                string wrapped = WrapInExecutorClass(ex.completion);

                var prov = new CSharpCodeProvider();
                var pars = new CompilerParameters {
                    GenerateExecutable = false,
                    GenerateInMemory   = true
                };

                // referencias .NET
                pars.ReferencedAssemblies.Add("System.dll");
                pars.ReferencedAssemblies.Add("System.Core.dll");
                pars.ReferencedAssemblies.Add("System.Web.Extensions.dll");

                // referencias Revit
                pars.ReferencedAssemblies.Add(revitApiPath);
                pars.ReferencedAssemblies.Add(revitApiUIPath);

                // mscorlib + runtime
                var runtimeDir = RuntimeEnvironment.GetRuntimeDirectory();
                pars.ReferencedAssemblies.Add(Path.Combine(runtimeDir, "mscorlib.dll"));
                pars.ReferencedAssemblies.Add(Path.Combine(runtimeDir, "System.Runtime.dll"));

                var results = prov.CompileAssemblyFromSource(pars, wrapped);

                if (results.Errors.HasErrors)
                {
                    var errs = results.Errors
                                  .Cast<CompilerError>()
                                  .Select(e => $"{e.Line}:{e.ErrorNumber} {e.ErrorText}")
                                  .ToArray();
                    // original prompt + errors
                    wFail.WriteLine(serializer.Serialize(new { prompt = ex.prompt, errors = errs }));
                    // full original example for manual fix
                    wCleanFail.WriteLine(serializer.Serialize(new { prompt = ex.prompt, completion = ex.completion, errors = errs }));
                }
                else
                {
                    wSucc.WriteLine(serializer.Serialize(ex));
                    wCleanSucc.WriteLine(serializer.Serialize(new { prompt = ex.prompt, completion = ex.completion }));
                }
            }

            Console.WriteLine("✅ Validación completada.");
            Console.WriteLine($"  Éxitos:            {successPath}");
            Console.WriteLine($"  Fallidos:          {failedPath}");
            Console.WriteLine($"  Limpios (OK):      {cleanSuccPath}");
            Console.WriteLine($"  Limpios (Fallidos):{cleanFailedFull}");
        }

        static string WrapInExecutorClass(string rawCode)
        {
            // 1) uidoc rename
            rawCode = rawCode.Replace("UIDocument uidoc =", "UIDocument localUidoc =");

            
            rawCode = rawCode.Replace("$", "");

            // 4) montar wrapper
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
            w.WriteLine();
            w.WriteLine("namespace DynamicCode");
            w.WriteLine("{");
            w.WriteLine("    public class Executor");
            w.WriteLine("    {");
            w.WriteLine("        public void Run(UIDocument uidoc, Document doc)");
            w.WriteLine("        {");
            w.WriteLine("            // Código IA inyectado:");
            w.WriteLine(rawCode);
            w.WriteLine();
            w.WriteLine("            // Regenerar la vista al final");
            w.WriteLine("            using (Transaction regenTx = new Transaction(doc, \"Regenerate View\"))");
            w.WriteLine("            {");
            w.WriteLine("                regenTx.Start();");
            w.WriteLine("                doc.Regenerate();");
            w.WriteLine("                regenTx.Commit();");
            w.WriteLine("            }");
            w.WriteLine("        }");
            w.WriteLine("    }");
            w.WriteLine("}");
            return w.ToString();
        }
    }
}