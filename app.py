
import os, json, asyncio, logging
import nest_asyncio
nest_asyncio.apply()

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
from google.genai import types
from hypoxemia_logic import hypoxemia_action_plan
from pressure_alarm_logic import classify_pressure_alarm
from weaning_logic import assess_weaning_readiness

logging.getLogger("google_genai.types").setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

SYSTEM_PROMPT = """
You are VentAssist, an expert AI clinical decision support tool
for mechanical ventilation in the ICU. Be concise — doctors are busy.

You have THREE clinical tools:
1. assess_hypoxemia      — for low SpO2 / oxygenation problems
2. assess_pressure_alarm — for high pressure alarms
3. assess_weaning        — for weaning and extubation readiness

Always call the right tool when clinical values are given.

WHEN VALUES ARE MISSING:
- Ask for ALL missing values in ONE single message.
- For weaning say: "To assess weaning readiness I need a few
  values — please provide: respiratory rate during trial, SpO2
  during trial, and whether the patient showed increased work
  of breathing (yes/no)."

EMERGENCY RULE:
- If SpO2 < 85%: say "Assess your patient NOW" first, then
  STILL call assess_hypoxemia and give the full action plan.

End every response with:
"This is decision support — verify with your clinical team."
"""

all_tools = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="assess_hypoxemia",
            description="Assess low SpO2 or oxygenation problems.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "spo2":         types.Schema(type=types.Type.NUMBER),
                    "fio2_percent": types.Schema(type=types.Type.NUMBER),
                    "current_peep": types.Schema(type=types.Type.NUMBER),
                    "pao2":         types.Schema(type=types.Type.NUMBER),
                },
                required=["spo2","fio2_percent","current_peep"]
            )
        ),
        types.FunctionDeclaration(
            name="assess_pressure_alarm",
            description="Troubleshoot high pressure alarms.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "peak_pressure":    types.Schema(type=types.Type.NUMBER),
                    "plateau_pressure": types.Schema(type=types.Type.NUMBER),
                    "peep":             types.Schema(type=types.Type.NUMBER),
                },
                required=["peak_pressure"]
            )
        ),
        types.FunctionDeclaration(
            name="assess_weaning",
            description="Assess weaning and extubation readiness.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "fio2_percent":           types.Schema(type=types.Type.NUMBER),
                    "peep":                   types.Schema(type=types.Type.NUMBER),
                    "gcs":                    types.Schema(type=types.Type.INTEGER),
                    "hemodynamically_stable": types.Schema(type=types.Type.BOOLEAN),
                    "no_new_sedation_24h":    types.Schema(type=types.Type.BOOLEAN),
                    "rr_during_trial":        types.Schema(type=types.Type.NUMBER),
                    "spo2_during_trial":      types.Schema(type=types.Type.NUMBER),
                    "no_distress":            types.Schema(type=types.Type.BOOLEAN),
                },
                required=["fio2_percent","peep","gcs",
                          "hemodynamically_stable","no_new_sedation_24h"]
            )
        ),
    ]
)

def execute_tool(name, args):
    if name == "assess_hypoxemia":
        return hypoxemia_action_plan(
            spo2=args["spo2"], fio2_percent=args["fio2_percent"],
            current_peep=args["current_peep"], pao2=args.get("pao2"))
    elif name == "assess_pressure_alarm":
        return classify_pressure_alarm(
            peak_pressure=args["peak_pressure"],
            plateau_pressure=args.get("plateau_pressure"),
            peep=args.get("peep", 5))
    elif name == "assess_weaning":
        return assess_weaning_readiness(
            fio2_percent=args["fio2_percent"], peep=args["peep"],
            gcs=args["gcs"],
            hemodynamically_stable=args["hemodynamically_stable"],            no_new_sedation_24h=args["no_new_sedation_24h"],
            rr_during_trial=args.get("rr_during_trial"),
            spo2_during_trial=args.get("spo2_during_trial"),
            no_distress=args.get("no_distress"))
    return {"error": "Unknown tool"}

async def ask_ventassist(question):
    client = genai.Client(
        api_key=os.environ.get("GOOGLE_API_KEY"),
        http_options={"api_version": "v1alpha"}
    )
    config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede"))),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    tools=[all_tools],
    system_instruction=types.Content(
        role="user",
        parts=[types.Part(text=SYSTEM_PROMPT)]
    ),
)

    tool_used      = None
    response_text  = ""
    transcript_buf = []

    async with client.aio.live.connect(
        model="models/gemini-2.5-flash-native-audio-latest",
        config=config
    ) as session:
        await session.send_client_content(
            turns=types.Content(role="user", parts=[types.Part(text=question)]),
            turn_complete=True
        )
        async for response in session.receive():
            if response.tool_call:
                for call in response.tool_call.function_calls:
                    tool_used = call.name
                    result    = execute_tool(call.name, dict(call.args))
                    await session.send_tool_response(
                        function_responses=[types.FunctionResponse(
                            id=call.id, name=call.name,
                            response={"result": json.dumps(result)}
                        )]
                    )
            elif hasattr(response, 'server_content') and response.server_content:
                content = response.server_content
                if hasattr(content, 'output_transcription') and content.output_transcription:
                    chunk = content.output_transcription.text
                    if chunk:
                        transcript_buf.append(chunk)
                if hasattr(content, 'turn_complete') and content.turn_complete:
                    if transcript_buf:
                        response_text = ''.join(transcript_buf)

    return {"response": response_text, "tool_used": tool_used}

@app.route('/')
def home():
    return send_file('ventassist_ui.html')

@app.route('/ask', methods=['POST'])
def ask():
    try:
        data     = request.get_json()
        question = data.get('question', '') if data else ''
        if not question:
            return jsonify({"error": "No question provided"}), 400
        loop   = asyncio.get_event_loop()
        result = loop.run_until_complete(ask_ventassist(question))
        return jsonify(result)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"response": f"Error: {str(e)}", "tool_used": None}), 500

@app.route('/health')
def health():
    return jsonify({"status": "VentAssist running ✅"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

