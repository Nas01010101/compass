// Gemini on Vertex AI (default) or the Gemini API when GEMINI_API_KEY is set.
import { GoogleGenAI, Type } from "@google/genai";

export const MODEL = process.env.MODEL || "gemini-3.8-flash";

let client;
function ai() {
  if (client) return client;
  client = process.env.GEMINI_API_KEY
    ? new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY })
    : new GoogleGenAI({
        vertexai: true,
        project: process.env.GOOGLE_CLOUD_PROJECT,
        location: process.env.GOOGLE_CLOUD_LOCATION || "global",
      });
  return client;
}

export async function generateJson(prompt, schema) {
  const res = await ai().models.generateContent({
    model: MODEL,
    contents: prompt,
    config: { responseMimeType: "application/json", responseSchema: schema, temperature: 0 },
  });
  return JSON.parse(res.text);
}

export { Type };
