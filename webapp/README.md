# Streamlit web demo

Built in **T39**. Run locally with:

```
make webapp
# or
streamlit run webapp/app.py
```

Then open http://localhost:8501.

## What it does

- Accepts a YouTube URL, uploaded video, or built-in demo.
- Runs the full \lecseg{} pipeline.
- Displays the video with a synchronised chapter / subtopic outline.
- Lets the user click any chapter or subtopic to jump in the video.

## Hosting

For supervisor / panel access we deploy to **Streamlit Community Cloud**.
Deployment instructions live in T39 once the demo is feature-complete.

## Privacy

The demo does **not** keep uploaded videos. Each session is in-memory only.
