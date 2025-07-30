using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Microsoft.CSharp;
using System;
using System.CodeDom.Compiler;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

namespace Revit_Agent_GPT_FT
{
    public static class Code_Executor
    {
        public static void Execute(UIDocument uidoc, string rawCode)
        {
            Document doc = uidoc.Document;
            string finalCodeToExecute;

            // Lógica inteligente para manejar la transacción
            if (rawCode.Trim().StartsWith("using (Transaction") || rawCode.Contains("tx.Start()"))
            {
                // Si la IA ya envía el bloque de transacción, simplemente lo usamos.
                // Es crucial que la IA también incluya doc.Regenerate() si es necesario.
                finalCodeToExecute = rawCode;
            }
            else
            {
                // Si la IA envía código limpio, nosotros lo envolvemos en una transacción segura.
                finalCodeToExecute = $@"
                    using (Transaction tx = new Transaction(doc, ""AI Generated Action""))
                    {{
                        tx.Start();
                        
                        {rawCode} // Inyectamos el código limpio

                        tx.Commit();
                    }}
                ";
            }

            // Plantilla final para compilar el código completo.
            // AHORA doc.Regenerate() ESTÁ DENTRO DEL MÉTODO QUE SE EJECUTA.
            string fullClassTemplate = $@"
                using Autodesk.Revit.DB;
                using Autodesk.Revit.DB.Structure;
                using Autodesk.Revit.UI;
                using Autodesk.Revit.UI.Selection;
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
                            // El código de la IA (con o sin transacción) se ejecuta primero.
                            {finalCodeToExecute}

                            // LA CORRECCIÓN: doc.Regenerate() se ejecuta después del código de la IA,
                            // pero DENTRO de un contexto que puede abrir una nueva transacción si es necesario.
                            // Para máxima seguridad, lo envolvemos en su propia transacción corta.
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

            // Configuración del compilador.
            CSharpCodeProvider provider = new CSharpCodeProvider();
            CompilerParameters parameters = new CompilerParameters
            {
                GenerateInMemory = true,
                GenerateExecutable = false
            };

            // Añadir las referencias DLL necesarias para la API de Revit.
            parameters.ReferencedAssemblies.Add("System.dll");
            parameters.ReferencedAssemblies.Add("System.Core.dll");
            parameters.ReferencedAssemblies.Add(typeof(Document).Assembly.Location); // RevitAPI.dll
            parameters.ReferencedAssemblies.Add(typeof(UIDocument).Assembly.Location); // RevitAPIUI.dll
            parameters.ReferencedAssemblies.Add(typeof(System.Windows.Forms.Form).Assembly.Location); // System.Windows.Forms.dll

            // Compilar el código.
            CompilerResults results = provider.CompileAssemblyFromSource(parameters, fullClassTemplate);

            if (results.Errors.HasErrors)
            {
                StringBuilder sb = new StringBuilder();
                sb.AppendLine("El código generado por la IA tiene errores y no se pudo compilar:\n");
                foreach (CompilerError error in results.Errors)
                {
                    // Restamos las líneas de la plantilla para dar al usuario la línea de error correcta.
                    // Ajustado a la nueva plantilla.
                    sb.AppendLine($"Línea {error.Line - 18}: {error.ErrorText}");
                }
                MessageBox.Show(sb.ToString(), "Error de Compilación del Código IA", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // Si la compilación es exitosa, ejecutar el código.
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
                // Captura errores de ejecución de la API de Revit (los más comunes).
                MessageBox.Show(ex.InnerException?.Message ?? ex.Message, "Error en Ejecución del Código IA", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
