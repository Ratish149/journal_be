import google.generativeai as genai
from django.utils import timezone

# Fallback API Key - REMOVED for security
# DEFAULT_KEY = ""


def get_gemini_key(excluded_keys=None):
    """
    Fetches an active Gemini API key from the database using a round-robin approach.
    Updates the last_used timestamp.
    """
    from core.models import GeminiApiKey

    # Get active keys ordered by last_used (least recently used first)
    queryset = GeminiApiKey.objects.filter(is_active=True)

    if excluded_keys:
        queryset = queryset.exclude(key__in=excluded_keys)

    active_keys = queryset.order_by("last_used")

    if not active_keys.exists():
        return None

    selected_key_obj = active_keys.first()
    selected_key_obj.last_used = timezone.now()
    selected_key_obj.usage_count += 1
    selected_key_obj.save(update_fields=["last_used", "usage_count"])

    return selected_key_obj.key


def analyze_trade_images(ltf_url=None, htf_url=None):
    """
    Analyzes LTF and HTF URLs using Gemini and returns a bias prediction and analysis.
    Sends URLs directly to the model in the prompt.
    """
    error_msg = "Gemini API key is not configured or all keys failed."
    max_retries = 3
    failed_keys = []

    for _ in range(max_retries):
        api_key = get_gemini_key(excluded_keys=failed_keys)
        if not api_key:
            break

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = f"""
            You are an expert trading analyst. I am providing you with two chart URLs for a trade journal entry:
            
            1. Higher Time Frame (HTF): {htf_url}
            2. Lower Time Frame (LTF): {ltf_url}
            
            Please access these URLs to view the charts, then analyze them to provide:
            1. Bias: (one word: Buy, Sell, or Neutral)
            2. Analysis: A concise explanation of why you see this bias based on market structure, supply/demand, or technical patterns visible in the charts.
            
            Format your response as:
            BIAS: [Bias]
            ANALYSIS: [Your analysis]
            """

            if not ltf_url and not htf_url:
                return (
                    "Unknown",
                    "No URLs provided to analyze.",
                )

            response = model.generate_content(prompt)
            content = response.text

            bias = "Neutral"
            analysis = content

            if "BIAS:" in content:
                parts = content.split("BIAS:", 1)[1].split("\n", 1)
                bias = parts[0].strip().title()
                if "ANALYSIS:" in content:
                    analysis = content.split("ANALYSIS:", 1)[1].strip()

            return bias, analysis

        except Exception as e:
            error_msg = str(e)

            print(f"API attempt failed with key {api_key}: {error_msg}")
            failed_keys.append(api_key)  # Track failed key to avoid reusing it

            # If it's a quota or auth error, continue to try next key
            if (
                "quota" in error_msg.lower()
                or "429" in error_msg
                or "api key" in error_msg.lower()
            ):
                continue
            else:
                # For other errors, we might want to fail early or try one more time
                continue

    return "Error", f"AI analysis failed after multiple attempts: {error_msg}"


def get_chat_response(entry, user_message, chat_history):
    """
    Provides a response to a user's message about a specific trade journal entry.
    Supports API key rotation on failure.
    """
    error_msg = "Gemini API key is not configured or all keys failed."
    max_retries = 3
    failed_keys = []

    for _ in range(max_retries):
        api_key = get_gemini_key(excluded_keys=failed_keys)
        if not api_key:
            break

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            history_list = list(chat_history)
            if history_list and history_list[-1].content == user_message:
                history_list.pop()

            previous_ref = ""
            if history_list:
                last_msg = history_list[-1]
                role_label = "Student" if last_msg.role == "user" else "Assistant"
                previous_ref = f"\nPrevious message ({role_label}): {last_msg.content}"

            context = f"""
            You are a trading mentor. Provide a short, simple, and direct explanation to the student.
            Avoid long-winded technical jargon unless necessary. Focus on clarity and brevity.
            I am a girl trader.
            Language Style:
            If the student asks in Romanized Nepali (mix of English and Nepali), respond in the same English-Nepali style. 
            Do not use Devanagari script (pure Nepali). Mirror the student's language and tone.
            {previous_ref}
            Trade Details:
            - Date: {entry.date}
            - Bias: {entry.bias}
            - Result: {entry.results}
            - P&L: {entry.pnl}
            - Kill Zone: {entry.kill_zone}
            - Array: {entry.array}
            - Reason: {entry.reason}
            - Mistake: {entry.mistake}
            - Emotions: {entry.emotions}
            - Before Trade Emotions: {entry.before_trade_emotions}
            - In Trade Emotions: {entry.in_trade_emotions}
            - After Trade Emotions: {entry.after_trade_emotions}
            """

            messages = [
                {"role": "user" if m.role == "user" else "model", "parts": [m.content]}
                for m in history_list
            ]

            chat = model.start_chat(history=messages)
            full_prompt = f"Context: {context}\n\nStudent: {user_message}"

            response = chat.send_message(full_prompt)
            return response.text

        except Exception as e:
            error_msg = str(e)
            print(f"Chat API attempt failed with key {api_key}: {error_msg}")
            failed_keys.append(api_key)

            if (
                "quota" in error_msg.lower()
                or "429" in error_msg
                or "api key" in error_msg.lower()
            ):
                continue
            else:
                continue

    return f"AI chat failed after multiple attempts: {error_msg}"
