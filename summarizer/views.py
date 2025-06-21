from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
import json
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re
import markdown
from django.conf import settings

# Set your Google GenAI API key here
genai.configure(api_key=settings.GENAI_API_KEY)

def index(request):
    return render(request, 'summarizer/index.html')

@csrf_exempt
def summarize_video(request):
    if request.method == "POST":
        data = json.loads(request.body)
        video_url = data.get("video_url")
        # Use a fixed prompt for summarization
        prompt = (
            "You are YouTube video summarizer. You will be taking the transcript text "
            "and summarizing the entire video and providing the important summary in points "
            "within 250 words. Please provide the summary of the text given here:"
        )

        # Extract video ID from URL
        match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", video_url)
        if not match:
            return JsonResponse({"error": "Invalid YouTube URL"}, status=400)
        video_id = match.group(1)

        # Get transcript
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([x['text'] for x in transcript])
        except Exception as e:
            return JsonResponse({"error": f"Transcript error: {str(e)}"}, status=400)

        # Summarize using Google GenAI (Gemini 1.5 Flash)
        try:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            full_prompt = f"{prompt}\n\n{transcript_text}"
            response = model.generate_content(full_prompt)
            summary = response.text
            # Split summary into paragraphs (by double newlines or single newlines)
            paragraphs = [p.strip() for p in summary.split('\n') if p.strip()]
        except Exception as e:
            return JsonResponse({"error": f"GenAI error: {str(e)}"}, status=500)

        # Generate evenly spaced breakpoints from transcript
        n = len(paragraphs)
        if n == 0:
            return JsonResponse({"summary_html": "", "breakpoints": []})
        transcript_times = [int(seg['start']) for seg in transcript]
        # Evenly spaced indices in transcript
        indices = [int(i * len(transcript_times) / n) for i in range(n)]
        breakpoints = [transcript_times[idx] for idx in indices]
        # Prepare YouTube timestamp links
        timestamp_links = [
            {
                "time": bp,
                "url": f"https://www.youtube.com/watch?v={video_id}&t={bp}s"
            }
            for bp in breakpoints
        ]
        # Prepare summary with markdown and return paragraphs and links
        summary_html = markdown.markdown(summary)
        return JsonResponse({
            "summary_html": summary_html,
            "breakpoints": timestamp_links,
            "paragraphs": paragraphs
        })

    return JsonResponse({"error": "Invalid request"}, status=400)