# LECSEG Streamlit Web App

Built in **T39**. Run locally with:

```
make webapp
# or
streamlit run webapp/app.py
```

Then open http://localhost:8501.

## What it does

- Lets a user paste a known LECSEG YouTube URL/video ID or select a benchmark lecture.
- Runs real repository segmentation methods on cached LECSEG assets.
- Displays the YouTube video, creator chapter reference, predicted chapter table, and timeline comparison.
- Reports Pk, WindowDiff, F1@2, tolerance-F1 context, and dataset-level modern metrics.
- Exports predicted chapters and creator-reference chapters as JSON.

## Scope

The app is a deployable benchmark explorer and local demonstration tool. It does
not fake arbitrary YouTube processing inside Streamlit. For a brand-new video,
first run the preprocessing pipeline to create transcript, sentence, embedding,
and chapter-reference files; then the lecture can be opened in the app.

## Hosting

For supervisor / panel access, deploy the repository to a machine that includes
the cached `data/` assets and Python dependencies, then run:

```
streamlit run webapp/app.py --server.port 8501
```

## Privacy

The app does not upload user data to external APIs. It reads local benchmark
assets and uses local Python methods only.
