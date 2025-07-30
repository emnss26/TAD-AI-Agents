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
using Revit_Agent_GPT_FT;

using System.Net.Http;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System.Xml.Linq;
using System.Net.Http.Headers;

namespace Revit_Agent_GPT_FT
{
    public partial class Form1 : System.Windows.Forms.Form
    {
        UIDocument uidoc;
        Autodesk.Revit.DB.Document doc;
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
            button1.Enabled = false;
            textBox2.Text = "Conectando con la IA...";

            try
            {
                string prompt = textBox1.Text.Trim();
                if (string.IsNullOrEmpty(prompt))
                {
                    MessageBox.Show(
                        "Por favor, introduce una instrucción.",
                        "Instrucción Vacía",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Information
                    );
                    return;
                }

                string generatedCode = await CallOpenAIAsync(prompt);

                if (string.IsNullOrWhiteSpace(generatedCode))
                {
                    MessageBox.Show(
                        "La IA devolvió una respuesta vacía.",
                        "Respuesta Vacía",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Warning
                    );
                    return;
                }

                textBox2.Text = generatedCode;

                DialogResult dr = MessageBox.Show(
                    "La IA ha generado este código. ¿Deseas ejecutarlo en Revit?\n\n" +
                    "Revisa el código antes de aceptar.",
                    "Confirmar Ejecución",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question
                );

                if (dr == DialogResult.Yes)
                {
                    Code_Executor.Execute(uidoc, generatedCode);
                }
                else
                {
                    TaskDialog.Show("Cancelado", "Ejecución cancelada por el usuario.");
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"Error al llamar a la IA:\n{ex.Message}",
                    "Error de IA",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
            finally
            {
                button1.Enabled = true;
            }
        }

        private Task<string> CallOpenAIAsync(string prompt)
        {
            // **************** SOLO PARA PRUEBAS ****************
            // No dejes tu API key en texto plano en producción.
            const string apiKey = "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";

            return Task.Run(async () =>
            {
                using (HttpClient client = new HttpClient())
                {
                    client.Timeout = TimeSpan.FromSeconds(300);
                    client.DefaultRequestHeaders.Authorization =
                        new AuthenticationHeaderValue("Bearer", apiKey);

                    var payload = new
                    {
                        model = "ft:gpt-3.5-turbo-1106:personal:revit-agent-v2:Bu13NbTZ",
                        messages = new object[]
                        {
                            new { role = "system", content = "Eres un asistente C# para Revit." },
                            new { role = "user",   content = prompt }
                        },
                        temperature = 0.0,
                        max_tokens = 2000
                    };

                    string jsonPayload = JsonConvert.SerializeObject(payload);
                    using (StringContent content = new StringContent(jsonPayload, Encoding.UTF8, "application/json"))
                    {
                        HttpResponseMessage response =
                            await client.PostAsync("https://api.openai.com/v1/chat/completions", content)
                                        .ConfigureAwait(false);

                        if (!response.IsSuccessStatusCode)
                        {
                            string err = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
                            throw new Exception($"OpenAI error {response.StatusCode}:\n{err}");
                        }

                        string body = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
                        JObject root = JObject.Parse(body);
                        return root["choices"]?[0]?["message"]?["content"]?.ToString().Trim() ?? "";
                    }
                }
            });
        }

    }
}
