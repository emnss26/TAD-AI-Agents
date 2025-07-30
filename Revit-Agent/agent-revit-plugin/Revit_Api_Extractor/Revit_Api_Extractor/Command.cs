using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;
using System.IO;
using System.Reflection;

namespace Revit_Api_Extractor
{
    [Transaction(TransactionMode.ReadOnly)]
    [Regeneration(RegenerationOption.Manual)]
    public class Command : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            var asm = typeof(Wall).Assembly;
            var list = new List<object>();
            foreach (var t in asm.GetTypes().Where(t => t.Namespace == "Autodesk.Revit.DB"))
            {
                var methods = t.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
                               .Select(m => new { m.Name, signature = m.ToString() });
                var props = t.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
                             .Select(p => p.Name);
                list.Add(new
                {
                    type = t.FullName,
                    methods = methods,
                    properties = props
                });
            }

            var outPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                "revit_api_reflection.json"
            );
            File.WriteAllText(outPath, JsonConvert.SerializeObject(list, Formatting.Indented));
            TaskDialog.Show("Dump", $"✅ JSON generado en:\n{outPath}");
            return Result.Succeeded;
        }
    }
}
