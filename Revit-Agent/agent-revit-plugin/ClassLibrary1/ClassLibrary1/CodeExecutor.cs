using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Microsoft.CSharp;
using System;
using System.CodeDom.Compiler;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

namespace ClassLibrary1
{
    public static class CodeExecutor
    {
        public static void Execute(UIDocument uidoc, string rawCode)
        {
            Document doc = uidoc.Document;

            // FILOSOFÍA DE SIMPLICIDAD RADICAL:
            // El Orquestador es el ÚNICO responsable de la transacción.
            string finalCodeToExecute = $@"
                using (Transaction tx = new Transaction(doc, ""AI Generated Action""))
                {{
                    tx.Start();
                    
                    // Inyectamos aquí el código 100% puro que recibimos de la IA.
                    {rawCode}

                    tx.Commit();
                }}
            ";

            // Plantilla final para compilar la clase completa.
            string fullClassTemplate = $@"
                // --- Namespaces Comunes de la API de Revit ---
                using Autodesk.Revit.DB;
                using Autodesk.Revit.DB.Structure;
                using Autodesk.Revit.DB.Architecture;
                using Autodesk.Revit.DB.Mechanical;
                using Autodesk.Revit.DB.Electrical;
                using Autodesk.Revit.DB.Plumbing;
                // ### CORRECCIÓN ###: La siguiente línea era incorrecta y ha sido eliminada.
                // using Autodesk.Revit.DB.Units; // <-- ERROR: 'Units' es una clase, no un namespace.
                
                // --- Namespaces de Interfaz de Usuario y Selección ---
                using Autodesk.Revit.UI;
                using Autodesk.Revit.UI.Selection;

                // --- Namespaces Fundamentales de .NET ---
                using System;
                using System.Collections.Generic;
                using System.Linq;
                using System.Windows.Forms;

                namespace DynamicCode
                {{
                    public class Executor
                    {{
                        public void Run(UIDocument uidoc, Document doc)
                        {{
                            // El código de la IA, ahora siempre envuelto en una transacción, se ejecuta aquí.
                            {finalCodeToExecute}

                            // La regeneración en su propia transacción es una práctica excelente para la estabilidad.
                            using (Transaction regenTx = new Transaction(doc, ""Regenerate View""))
                            {{
                                regenTx.Start();
                                doc.Regenerate();
                                regenTx.Commit();
                            }}
                        }}
                    }}
                }}
            ";

            // --- LÓGICA DE COMPILACIÓN Y EJECUCIÓN ---
            CSharpCodeProvider provider = new CSharpCodeProvider();
            CompilerParameters parameters = new CompilerParameters
            {
                GenerateInMemory = true,
                GenerateExecutable = false
            };

            parameters.ReferencedAssemblies.Add("System.dll");
            parameters.ReferencedAssemblies.Add("System.Core.dll");
            parameters.ReferencedAssemblies.Add(typeof(Document).Assembly.Location);
            parameters.ReferencedAssemblies.Add(typeof(UIDocument).Assembly.Location);
            parameters.ReferencedAssemblies.Add(typeof(System.Windows.Forms.Form).Assembly.Location);

            CompilerResults results = provider.CompileAssemblyFromSource(parameters, fullClassTemplate);

            if (results.Errors.HasErrors)
            {
                var sb = new StringBuilder();
                sb.AppendLine("El código generado por la IA tiene errores y no se pudo compilar:\n");
                foreach (CompilerError error in results.Errors)
                {
                    // Ajustamos el cálculo de la línea de error para reflejar la plantilla corregida.
                    sb.AppendLine($"Línea {error.Line - 29}: {error.ErrorText}");
                }
                MessageBox.Show(sb.ToString(), "Error de Compilación del Código IA", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            Assembly assembly = results.CompiledAssembly;
            Type program = assembly.GetType("DynamicCode.Executor");
            object instance = Activator.CreateInstance(program);
            MethodInfo mainMethod = program.GetMethod("Run");

            try
            {
                mainMethod.Invoke(instance, new object[] { uidoc, doc });
                TaskDialog.Show("Éxito", "El comando de la IA se ha ejecutado correctamente en Revit.");
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.InnerException?.Message ?? ex.Message, "Error en Ejecución del Código IA", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
