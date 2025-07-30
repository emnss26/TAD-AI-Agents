using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using ClassLibrary1;

using System.Net.Http;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System.Xml.Linq;


namespace ClassLibrary1
{
    public partial class Form1 : System.Windows.Forms.Form
    {
        UIDocument uidoc;
        Autodesk.Revit.DB.Document doc;

        private const string ORCHESTRATOR_URL = "http://127.0.0.1:5000/process_instruction";
        public Form1(Autodesk.Revit.UI.UIDocument uidoc, Autodesk.Revit.DB.Document doc)
        {
            InitializeComponent();
            this.uidoc = uidoc;
            this.doc = doc;
        }

        private void Form1_Load(object sender, EventArgs e)
        {

        }

        private async void button1_Click(object sender, EventArgs e)
        {
            string userPrompt = textBox1.Text;
            if (string.IsNullOrWhiteSpace(userPrompt)) { /*...*/ return; }

            button1.Enabled = false;
            textBox2.Clear();
            textBoxChat.AppendText($"\r\n[TÚ]: {userPrompt}");
            textBoxChat.AppendText("\r\n[SISTEMA]: Obteniendo contexto de Revit...");

            // --- PASO 0: RECOLECTAR CONTEXTO DEL MODELO ---
            // Recolectamos los nombres de los niveles para ayudar al orquestador.
            var revitContext = new
            {
                available_levels = new FilteredElementCollector(doc)
           .OfClass(typeof(Level))
           .Cast<Level>()
           .OrderBy(l => l.Elevation)
           .Select(l => l.Name)
           .ToList(),

                available_wall_types = new FilteredElementCollector(doc)
           .OfClass(typeof(WallType))
           .Cast<WallType>()
           .Select(wt => wt.Name)
           .ToList(),

                // Puedes añadir más contexto aquí según sea necesario
                // available_door_types = ...
            };

            textBoxChat.AppendText($"\r\n[SISTEMA]: Contexto preparado. Contactando al orquestador...");

            using (var client = new HttpClient())
            {
                try
                {
                    client.Timeout = TimeSpan.FromSeconds(3000);

                    // AHORA el payload incluye el texto Y el contexto
                    var payload = new { text = userPrompt, context = revitContext };
                    string jsonPayload = JsonConvert.SerializeObject(payload);
                    var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                    var response = await client.PostAsync(ORCHESTRATOR_URL, content);

                    // ... (el resto del código para manejar la respuesta, confirmación y ejecución es idéntico al de la respuesta anterior)
                    if (!response.IsSuccessStatusCode)
                    {
                        string errorContent = await response.Content.ReadAsStringAsync();
                        MessageBox.Show($"Error en el Orquestador ({response.StatusCode}):\n{errorContent}", "Error de Servidor", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        textBoxChat.AppendText($"\r\n[ERROR]: Falla de comunicación con el orquestador.");
                        return;
                    }

                    string responseBody = await response.Content.ReadAsStringAsync();
                    var resultObject = JObject.Parse(responseBody);

                    string generatedCode = resultObject["generated_code"]?.ToString() ?? string.Empty;

                    textBoxChat.AppendText($"\r\n[ORQUESTADOR]: Análisis completado. Código recibido.");
                    textBox2.Text = generatedCode;

                    if (string.IsNullOrWhiteSpace(generatedCode) || generatedCode.Trim().StartsWith("// Error"))
                    {
                        MessageBox.Show("El agente no pudo generar el código.", "Error de Generación", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        textBoxChat.AppendText("\r\n[AGENTE]: Fallo al generar el código.");
                        return;
                    }

                    DialogResult userConfirmation = MessageBox.Show(
                        "El agente ha generado código. ¿Deseas ejecutarlo?", "Confirmar Ejecución",
                        MessageBoxButtons.YesNo, MessageBoxIcon.Question);

                    if (userConfirmation == DialogResult.Yes)
                    {
                        textBoxChat.AppendText("\r\n[SISTEMA]: Ejecutando código en Revit...");
                        CodeExecutor.Execute(this.uidoc, generatedCode);
                        textBoxChat.AppendText("\r\n[REVIT]: Comando enviado para ejecución.");
                    }
                    else
                    {
                        textBoxChat.AppendText("\r\n[SISTEMA]: Ejecución cancelada.");
                        TaskDialog.Show("Cancelado", "La ejecución del código ha sido cancelada.");
                    }
                }
                catch (Exception ex)
                {
                    string errorMessage = ex.InnerException?.Message ?? ex.Message;
                    MessageBox.Show($"Ocurrió un error: {errorMessage}", "Error General", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    textBoxChat.AppendText($"\r\n[ERROR]: {errorMessage}");
                }
                finally
                {
                    button1.Enabled = true;
                    textBox1.Clear();
                }
            }
        }

    

        private void textBox1_TextChanged(object sender, EventArgs e)
        {

        }

        private void textBoxChat_TextChanged(object sender, EventArgs e)
        {

        }
    }
}
