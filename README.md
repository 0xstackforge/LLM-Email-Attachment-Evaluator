# Doczen: Code Challenge

## Task 1

Build classification and evaluation for email attachments from `.eml` files in `examples/`.

Each email contains an HTML body and attachments. Classify every attachment into exactly one of two groups:

* **relevant** — attachments used to extract meaningful information from the email
* **irrelevant** — attachments that are noise in the HTML (e.g., social icons, company logos, signature images)

Classification must be based only on the email’s HTML body. Do not use attachment contents, MIME types, filenames, headers, or other metadata.

Build two Python scripts:

1. A script that reads `examples/*.eml`, extracts the HTML body and attachment filenames, and uses the Anthropic Claude API to classify each attachment into `relevant` or `irrelevant`. It must generate `output/attachments_XXXXX.json`.
2. A script that evaluates the generated output against ground truth in `ground_truth/`.

## Input

```
examples/
  example_00001.eml
  example_00002.eml
  ...
```

## Output

```
output/
  attachments_00001.json
  attachments_00002.json
  ...
```

Example:

```json
{
  "relevant": [
    "example_00001_attachment_02.pdf",
    "example_00001_attachment_03.pdf",
    "example_00001_attachment_04.pdf",
    "example_00001_attachment_05.pdf",
    "example_00001_attachment_06.png"
  ],
  "irrelevant": [
    "example_00001_attachment_01.jpg"
  ]
}
```

## Ground truth

```
ground_truth/
  attachments_00001.json
  attachments_00002.json
  attachments_00003.json
  attachments_00004.json
```

## Task 2

Uses the same dataset and scripts from Task 1. Details will be provided during the live coding session.

