# 📖 GLOSSARY — Every Term, Plain English

**When you find a word anywhere in the project that you don't know — search here.**
Alphabetical. One line per term.

---

### Ablation
Turning off a single component of your model to isolate how much that component helps.

### Accuracy
Fraction of predictions that match the ground truth. Not always the right metric (see F1, Pk).

### Annotation
Labelling data by hand. For us: writing down where a topic boundary is.

### ASR (Automatic Speech Recognition)
Turning speech into text. Whisper is the best open-source ASR.

### Batch size
How many items the model processes at once. Bigger batch = faster training but more GPU memory.

### Bias
A systematic error in a model (e.g., always predicting "no boundary"). Opposite of variance.

### Boundary
A single time-point separating two topics/chapters. A video with 5 chapters has 4 boundaries (t=0 isn't a boundary).

### Bootstrap
A way to estimate uncertainty: resample your data 1000× with replacement and recompute the statistic each time.

### BracU
BRAC University, our home institution.

### Cache
A stored copy of an expensive computation so the next call is instant.

### Chapter
A top-level segment (~5–15 min) in a lecture. For us: the ground-truth unit from YouTube creator timestamps.

### Checkpoint
Saved weights of a neural model partway through training.

### CLIP
OpenAI's image+text encoder. Produces a vector for an image and a vector for text in the same space.

### CLI
Command Line Interface — tools you run in the terminal by typing commands.

### Commit (Git)
A snapshot of your code. Every commit has a message explaining what changed.

### Conda
A package manager for Python + non-Python dependencies. We use `venv + pip` instead.

### Config
A YAML file listing hyperparameters. Keeps code flexible without editing source.

### Confidence interval (CI)
A range in which the true value of a statistic probably lies (95% CI = 95% probability).

### Confusion matrix
A table of (true label) × (predicted label) counts.

### Context window
How many tokens an LLM can read at once.

### Corpus
A collection of texts.

### Cosine similarity
Dot product of two normalised vectors. Between -1 and 1. Higher = more similar.

### Cross-validation (CV)
Split data into K folds; train on K-1, test on 1; rotate; average.

### CUDA
NVIDIA's GPU computing platform. If you have an NVIDIA GPU, PyTorch uses CUDA automatically.

### Dataset
A collection of (input, label) pairs the model learns from or is evaluated on.

### Deep learning
A subset of machine learning using neural nets with many layers.

### DOI
Digital Object Identifier — a permanent link to an academic artefact (paper, dataset).

### Docker
A way to ship an entire OS+dependencies setup. We are NOT using Docker for LECSEG (too complex for this project).

### Embedding
A list of numbers that represents a word, sentence, or image in vector form.

### Epoch
One full pass through the training dataset.

### Error analysis
Looking at the model's mistakes by hand to find patterns.

### F1 score
Harmonic mean of precision and recall. Between 0 and 1. Higher = better.

### FAISS
A fast library for similarity search over large vector collections. We don't need it for 30 videos.

### faster-whisper
A reimplementation of OpenAI's Whisper using CTranslate2 that runs ~4× faster. Same quality.

### FFmpeg
A command-line tool to convert audio/video formats. We use it to extract `.wav` from `.mp4`.

### Fine-tuning
Taking a pretrained model and training it further on your specific task.

### f0 (fundamental frequency)
The pitch of a voice. Measured in Hz.

### Fold
One of the K splits in cross-validation.

### Forward pass
Running input through a neural net to get an output. No learning happens.

### Fusion
Combining information from multiple sources (modalities).

### Gate
A learned scalar between 0 and 1 that controls how much of a signal to use.

### GitHub
Where our code lives. https://github.com/

### Git LFS
Git Large File Storage. For big binary files that plain Git would choke on.

### GPU
Graphics Processing Unit. Specialised chip that makes deep learning 100× faster than CPU.

### Gradient
The slope of the loss with respect to a parameter. Tells the model which way to move.

### Ground truth (GT)
The "correct" label. What the model is scored against.

### Hallucination
When an LLM makes up facts that sound plausible but aren't true.

### H-WD
Hierarchical WindowDiff — our hierarchical version of the WD metric. Lower is better. (N6.)

### Hyperparameter
A setting you choose *before* training (learning rate, batch size). Opposite of parameter.

### Hugging Face
Platform for hosting open-source models and datasets. https://huggingface.co

### Hydra
A config system. Lets you swap hyperparameters via command line.

### Idempotent
Running the same operation twice gives the same result as running it once. Important for long jobs.

### Inference
Using a trained model to make predictions.

### Inter-annotator agreement (IAA)
How much two humans agree on the same labels. Cohen's κ is one way to measure it.

### JSON / JSONL
JavaScript Object Notation / JSON Lines (one JSON object per line). A data format.

### Jupyter notebook
An interactive Python editor. Good for exploration, not for production.

### Keyframe
One representative frame picked out of a shot.

### KMeans
A clustering algorithm that groups points into K clusters.

### Kappa (κ)
Cohen's kappa. Inter-annotator agreement adjusted for chance.

### LaTeX
A typesetting system used for academic papers. Our thesis compiles via `pdflatex`.

### LECSEG-30
Our dataset: 30 YouTube lecture videos with chapter + subtopic labels.

### LLM
Large Language Model. Big neural nets for text. Examples: GPT-4, Llama 3.1, Mistral.

### Logits
The raw numerical output of a neural net, before softmax.

### Loss
A number the optimiser tries to minimise during training.

### Makefile
A file with named commands (e.g., `make reproduce`). Saves typing long shell commands.

### Manifest
A machine-readable index of our dataset. `data/manifest.jsonl` lists every video and its metadata.

### Matplotlib
Python plotting library. We make all thesis figures with it.

### Metric
A number that measures how good a prediction is (Pk, WD, F1, BS, H-WD).

### Modality
A type of input: text, audio, image.

### MOOC
Massive Open Online Course (Coursera, edX, ...). Many of our test videos come from MOOCs.

### MPNet
A strong sentence-embedding model. Output dim 768.

### Neural net
A function made of stacked linear layers + non-linearities. Learned from data.

### Normalisation (vector)
Scaling a vector so its length is 1. Makes cosine similarity = dot product.

### numpy
Python array library. Every ML library uses it.

### OCR
Optical Character Recognition. Turning slide pixels into text.

### Ollama
A tool for running open LLMs locally.

### Overfitting
When your model memorises training data and does poorly on new data.

### Paired test (statistics)
A statistical test that compares two methods on *the same* data points (here: the same videos).

### Pandas
Python library for tables. We use it for all CSV manipulation.

### Parameter
A number the model learns. Opposite of hyperparameter.

### Parquet
A columnar binary file format. Fast to read/write, small.

### Pk
A segmentation metric. Lower is better.

### Precision
Of all boundaries predicted, fraction that are correct.

### Pretrained
A model that someone else already trained, which we use as a starting point.

### Prompt
The input you give an LLM.

### Prosody
How something is said (pauses, pitch, rhythm). Not what.

### PyTorch
Our deep-learning framework.

### Ramdom seed
A number that controls pseudo-randomness. Same seed = same results. Required for reproducibility.

### Recall
Of all true boundaries, fraction predicted. Opposite trade-off of precision.

### Reproducibility
The property that anyone can run your code and get the same numbers.

### Ruff
A Python linter (checks for style issues).

### SBERT
Sentence-BERT. Produces sentence embeddings.

### Seed
See Random seed.

### segeval
A Python library that implements Pk, WD, BS.

### Segmentation
Splitting a long thing (text, video) into pieces.

### Sentence boundary disambiguation
The task of deciding where one sentence ends and the next begins.

### Shot
A continuous run of frames without a visual cut.

### Softmax
A function that turns any vector into probabilities that sum to 1.

### SOTA (state-of-the-art)
The best currently known method for a task.

### Streamlit
A Python library to quickly build a web UI from a script. Our demo uses it.

### Subtopic
A fine-grained segment inside a chapter.

### Tokenization
Splitting text into chunks the model can consume (words, subwords, or bytes).

### Topic model
A model that assigns themes to documents (e.g., LDA). Related to segmentation but not identical.

### TransNetV2
An open shot-boundary detection model we use.

### Transformer
The architecture behind BERT, GPT, CLIP. Self-attention over a sequence.

### Turnitin
Plagiarism-detection service BracU uses.

### tqdm
A progress-bar library.

### Typer
A Python library for building CLIs.

### Venue
The conference or journal a paper is published in.

### Virtual environment (venv)
An isolated Python installation for one project.

### Viterbi
A dynamic-programming algorithm that finds the most probable path through a sequence.

### VS Code
Our code editor. Free. From Microsoft.

### WD (WindowDiff)
A segmentation metric. Lower = better.

### Weights (model)
The learned parameters of a neural net.

### Whisper
OpenAI's open speech-recognition model.

### Wilcoxon signed-rank
A non-parametric paired test. We use it for T30.

### YAML
A human-readable config-file format. Used in `progress.yaml` and all Hydra configs.

### yt-dlp
A command-line YouTube downloader. Maintained fork of youtube-dl.

### Zenodo
An open academic data repository. We deposit LECSEG-30 there.
