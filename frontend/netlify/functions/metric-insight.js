exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return jsonResponse(405, { error: "Method not allowed" });
  }

  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    return jsonResponse(503, { error: "GROQ_API_KEY is not configured" });
  }

  let payload;
  try {
    payload = JSON.parse(event.body || "{}");
  } catch {
    return jsonResponse(400, { error: "Invalid JSON" });
  }

  const bankCode = String(payload.bankCode || "");
  const insight = payload.insight;
  if (!bankCode || !insight?.metric?.label) {
    return jsonResponse(400, { error: "Missing bankCode or insight payload" });
  }

  const isFY25 = insight.metric.coverage === "fy25";
  const systemPrompt = isFY25
    ? "You are a careful banking analyst. You are evaluating an FY25-only metric. Do not pretend there is a trend. Do not mention or compute year-on-year comparisons, movements, or percentage changes. Explain the metric exclusively as an FY25 composition/driver using the provided numeric decomposition and transcript evidence."
    : "You are a careful banking analyst. Explain the multi-year financial metric using the numeric context provided and extract insight from the transcript evidence to explain the trend direction. If evidence is weak or adjacent, clearly qualify it.";

  const prompt = buildPrompt(bankCode, insight);

  const tools = [
    {
      type: "function",
      function: {
        name: "ask_user_analyst_note",
        description: "Invoke this tool if there is completely insufficient management commentary or evidence to explain the metric, requiring the user to manually add an analyst note.",
        parameters: {
          type: "object",
          properties: {
            reason: {
              type: "string",
              description: "The reason why manual context is needed."
            }
          },
          required: ["reason"]
        }
      }
    }
  ];

  try {
    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: process.env.INSIGHTS_MODEL || "llama-3.3-70b-versatile",
        temperature: 0.2,
        max_tokens: 420,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: prompt }
        ],
        tools: tools,
        tool_choice: "auto"
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return jsonResponse(response.status, { error: errorText.slice(0, 500) });
    }

    const completion = await response.json();
    const message = completion?.choices?.[0]?.message;

    if (message?.tool_calls && message.tool_calls.length > 0) {
      const toolCall = message.tool_calls.find((tc) => tc.function.name === "ask_user_analyst_note");
      if (toolCall) {
        return jsonResponse(200, { askUser: true });
      }
    }

    const takeaway = message?.content || "";
    return jsonResponse(200, { takeaway });
  } catch (error) {
    return jsonResponse(500, { error: error instanceof Error ? error.message : "Unknown error" });
  }
};

function buildPrompt(bankCode, insight) {
  const isFY25 = insight.metric.coverage === "fy25";

  const movement = isFY25
    ? `${insight.metric.label}: ${insight.currentValue} in ${insight.currentYear}\nNo year-on-year comparison available from the uploaded workbook.`
    : (insight.previousYear && insight.previousValue
      ? `${insight.metric.label}: ${insight.previousValue} in ${insight.previousYear} to ${insight.currentValue} in ${insight.currentYear}. Absolute change: ${insight.absoluteChange || "N/A"}. Percent change: ${insight.percentChange || "N/A"}.`
      : `${insight.metric.label}: ${insight.currentValue} in ${insight.currentYear}. Year-on-year movement is not available from the uploaded workbook.`);

  const evidence = (insight.evidence || [])
    .slice(0, 6)
    .map(
      (item, index) =>
        `${index + 1}. Topic: ${item.topic}; Period: ${item.quarter || "Transcript"} ${item.callDate}; Excerpt: ${item.excerpt}`
    )
    .join("\n");

  const numericNotes = (insight.numericNotes || []).map((note) => `- ${note}`).join("\n");

  return `Bank: ${bankCode}
Metric coverage: ${insight.metric.coverage}
Evidence strength: ${insight.evidenceStrength}

Metric Details:
${movement}

Financial Decomposition Tool Output (Numeric breakdown):
${numericNotes || "- Not available"}

Keyword / Adjacent Topic Transcript Evidence:
${evidence || "No direct transcript evidence was found. You should strongly consider using the ask_user_analyst_note tool unless the decomposition clearly tells the story."}

Write one concise analyst takeaway in 3-5 sentences. Link the metric to the transcript evidence. Maintain strict adherence to your system prompt.`;
}

function jsonResponse(statusCode, payload) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  };
}
