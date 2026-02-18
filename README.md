# Email Attachment Intelligence

A production-ready document intelligence pipeline that classifies email attachments from `.eml` files as **relevant** or **irrelevant**, using only the email’s HTML body context.

This system leverages the Anthropic Claude API for contextual reasoning and includes an evaluation module for performance benchmarking against ground truth data.

---

## 🚀 Overview

The project processes `.eml` email files and performs the following:

1. Extracts:
   - HTML body
   - Attachment filenames

2. Classifies each attachment into exactly one category:
   - `relevant`
   - `irrelevant`

3. Generates structured JSON output files.

4. Evaluates predictions against labeled ground truth using standard classification metrics.

---

## 🧠 Classification Rules

Classification must rely **exclusively on the email’s HTML body**.

The following information **must not** be used:
- Attachment contents
- MIME types
- Filenames
- Headers
- Any metadata

This constraint simulates real-world scenarios where reasoning must be based solely on rendered email content.

---

## 📂 Project Structure

```text
doczen/
│
├── examples/
│   ├── example_00001.eml
│   ├── example_00002.eml
│   └── ...
│
├── ground_truth/
│   ├── attachments_00001.json
│   ├── attachments_00002.json
│   └── ...
│
├── output/
│
├── classify_attachments.py
├── evaluate.py
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/doczen.git
cd doczen
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Example `requirements.txt`:

```
anthropic
beautifulsoup4
tqdm
scikit-learn
```

---

## 🔐 Environment Configuration

Set your Anthropic API key:

**macOS/Linux**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

**Windows**
```bash
set ANTHROPIC_API_KEY=your_key_here
```

---

# 📌 Component 1: Attachment Classification

## Purpose

Reads `.eml` files from `examples/`, extracts HTML content and attachment filenames, and classifies attachments using Claude.

## Run

```bash
python classify_attachments.py
```

## Output

Generated files:

```text
output/
  attachments_00001.json
  attachments_00002.json
  ...
```

Example output:

```json
{
  "relevant": [
    "example_00001_attachment_02.pdf"
  ],
  "irrelevant": [
    "example_00001_attachment_01.jpg"
  ]
}
```

Each attachment must appear in exactly one category.

---

## 🧩 Prompt Strategy

The model receives:
- Full HTML body
- List of attachment filenames

It is instructed to:
- Identify attachments materially referenced in the email
- Detect decorative or structural HTML elements (logos, icons, signature images)
- Return strictly structured JSON output
- Avoid explanations

---

# 📊 Component 2: Evaluation

## Purpose

Compares generated outputs against ground truth labels.

## Run

```bash
python evaluate.py
```

## Metrics Computed

- Accuracy
- Precision
- Recall
- F1 Score
- Per-file breakdown
- Macro-averaged summary

Each attachment is treated as a binary classification:
- Positive → relevant
- Negative → irrelevant

---

## 📈 Evaluation Methodology

Ground truth files must match output naming format:

```text
ground_truth/attachments_00001.json
```

Evaluation compares attachment-level predictions against reference labels.

---

# 🏗️ Design Principles

### Deterministic Output
Strict JSON formatting enables automated validation and evaluation.

### Separation of Concerns
- `classify_attachments.py` handles inference
- `evaluate.py` handles benchmarking

### Reproducibility
Consistent file naming and structured outputs ensure experiment tracking.

---

# 🛡️ Error Handling & Validation

The classification pipeline includes:
- API retry handling
- JSON schema validation
- Attachment coverage verification
- Logging for malformed responses

---

# 🔄 Example Workflow

```bash
# Step 1: Generate classifications
python classify_attachments.py

# Step 2: Evaluate performance
python evaluate.py
```

---

# 🚀 Production Considerations

- Rate limiting and exponential backoff
- Deterministic JSON validation
- Cost monitoring for API usage
- Parallel processing support
- Prompt versioning
- CI-based regression evaluation

---

# 🔮 Extensibility

This pipeline can be extended to support:

- Confidence scoring
- Multi-class categorization
- Prompt optimization experiments
- Async API batching
- Docker deployment
- Model comparison benchmarking

---

# 📜 License

MIT License

Copyright (c) 2026 Will
