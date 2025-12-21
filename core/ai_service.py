from io import BytesIO

import google.generativeai as genai
import requests
from django.utils import timezone
from PIL import Image

# Fallback API Key in case database is empty
DEFAULT_KEY = "AIzaSyDimiOmGZKUAGO-ce1T9fNVmI49ECNcdDw"


def get_gemini_key():
    """
    Fetches an active Gemini API key from the database using a round-robin approach.
    Updates the last_used timestamp.
    """
    from core.models import GeminiApiKey

    # Get active keys ordered by last_used (least recently used first)
    active_keys = GeminiApiKey.objects.filter(is_active=True).order_by("last_used")

    if not active_keys.exists():
        return DEFAULT_KEY

    selected_key_obj = active_keys.first()
    selected_key_obj.last_used = timezone.now()
    selected_key_obj.usage_count += 1
    selected_key_obj.save(update_fields=["last_used", "usage_count"])

    return selected_key_obj.key


def analyze_trade_images(ltf_url, htf_url):
    """
    Analyzes LTF and HTF images using Gemini and returns a bias prediction and analysis.
    Supports API key rotation on failure.
    """
    error_msg = "Gemini API key is not configured or all keys failed."
    max_retries = 3  # Try up to 3 different keys if available

    for _ in range(max_retries):
        api_key = get_gemini_key()
        if not api_key:
            break

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = """
            You are an expert trading analyst. I am providing you with two chart images for a trade journal entry:
            1. Higher Time Frame (HTF)
            2. Lower Time Frame (LTF)
            
            Please analyze these images and provide:
            1. Bias: (one word: Buy, Sell, or Neutral)
            2. Analysis: A concise explanation of why you see this bias based on market structure, supply/demand, or technical patterns visible in the charts.
            
            Format your response as:
            BIAS: [Bias]
            ANALYSIS: [Your analysis]
            """

            images = []

            # Helper to fetch image from URL
            def fetch_image(url):
                if not url:
                    return None
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Referer": "https://www.tradingview.com/",
                    }
                    # Bypass potential system proxy issues using proxies={"http": None, "https": None}
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=15,
                        proxies={"http": None, "https": None},
                    )
                    if response.status_code == 200:
                        content_type = response.headers.get("Content-Type", "").lower()

                        if "text/html" in content_type:
                            import re

                            # Support both single and double quotes for the snapshot URL
                            img_match = re.search(
                                r'https://s3\.tradingview\.com/snapshots/[^"\'\s>]+\.png',
                                response.text,
                            )
                            if img_match:
                                direct_url = img_match.group(0)
                                response = requests.get(
                                    direct_url,
                                    headers=headers,
                                    timeout=10,
                                    proxies={"http": None, "https": None},
                                )
                                if response.status_code != 200:
                                    return None
                            else:
                                print(f"No image URL found in HTML for {url}")
                                return None

                        return Image.open(BytesIO(response.content))
                except Exception as e:
                    print(f"Error fetching image from {url}: {e}")
                return None

            htf_img = fetch_image(htf_url)
            ltf_img = fetch_image(ltf_url)

            if htf_img:
                images.append(htf_img)
            if ltf_img:
                images.append(ltf_img)

            if not images:
                return (
                    "Unknown",
                    "No valid images found at the provided URLs to analyze.",
                )

            response = model.generate_content([prompt] + images)
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
            print(
                f"API attempt failed with key starting with {api_key[:5]}: {error_msg}"
            )
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

    for _ in range(max_retries):
        api_key = get_gemini_key()
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
            
            Language Style:
            If the student asks in Romanized Nepali (mix of English and Nepali), respond in the same English-Nepali style. 
            Do not use Devanagari script (pure Nepali). Mirror the student's language and tone.
            {previous_ref}
            
            Trade Details:
            - Date: {entry.date}
            - Bias: {entry.bias}
            - P&L: {entry.pnl}
            - Reason: {entry.reason}
            - Mistake: {entry.mistake}
            - AI Bias Prediction: {entry.ai_bias_prediction}
            - AI Analysis: {entry.ai_analysis}
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
            print(
                f"Chat API attempt failed with key starting with {api_key[:5]}: {error_msg}"
            )
            if (
                "quota" in error_msg.lower()
                or "429" in error_msg
                or "api key" in error_msg.lower()
            ):
                continue
            else:
                continue

    return f"AI chat failed after multiple attempts: {error_msg}"
