# Multimodal Evaluation: Images, Documents & Visual Token Economics

## Contents
1. [Multimodal Evaluation Overview](#1-multimodal-evaluation-overview)
2. [Passing Images: Base64 Data URLs Only](#2-passing-images-base64-data-urls-only)
3. [PDF & Document Workarounds](#3-pdf--document-workarounds)
4. [The Patch Budget & Token Math](#4-the-patch-budget--token-math)
5. [Detail Levels: low, high, and original](#5-detail-levels-low-high-and-original)
6. [The `low` Detail Trap Across Model Families](#6-the-low-detail-trap-across-model-families)
7. [Visual Text Limitations & Detection-Based Cropping](#7-visual-text-limitations--detection-based-cropping)
8. [Rules, Reasons, and Counter-Examples](#8-rules-reasons-and-counter-examples)

---

## 1. Multimodal Evaluation Overview
The Decisions API evaluates images directly alongside text in a single forward pass. It supports visual triage, product photo verification, signature detection, document layout inspection, and damage assessments without requiring intermediate OCR or descriptive captioning models.

---

## 2. Passing Images: Base64 Data URLs Only
Images must be sent as inline base64-encoded data URLs within content parts of `user` messages [documented as of 2026-10-21]:

```python
import base64

def encode_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"

content = [
    {"type": "input_text", "text": "Inspect the photo of the returned item."},
    {"type": "input_image", "image_url": encode_image(photo_bytes), "detail": "low"}
]
```

### Strict Wire Constraints
- **Data URLs Only**: Public HTTP/HTTPS URLs and `file_id` references are **rejected** with HTTP 400 [documented].
- **Maximum Image Count**: Up to 128 images per request [documented].
- **No Non-User Messages**: Content parts must be wrapped inside a message with `"role": "user"`.

---

## 3. PDF & Document Workarounds
The Decisions API has **no native PDF support** [documented]. The appropriate workaround depends on document structure:

### Path A: Text-Extractable PDFs (Agreements, Terms, Digital Reports)
Extract text directly using `pypdf` or `pdfplumber` and send as `input_text`.
- *Advantages*: Zero image token overhead, 10x lower cost, faster processing.
- *Preservation*: Retain section headers, bullet structure, and page markers.

### Path B: Scanned or Layout-Dependent PDFs (Invoices, Tax Forms, Signed Declarations)
Rasterize specific pages to PNG or JPEG using `pdf2image` or `pypdfium2` and submit as `input_image` blocks.
- *Selective Slicing*: Never rasterize an entire 50-page document. Use an initial text scan or page classifier to select only the target pages (e.g., signature block or summary invoice table).
- *Resolution*: Render at 150–200 DPI to avoid exceeding patch limits while maintaining legibility.

---

## 4. The Patch Budget & Token Math

The model processes images by dividing them into $32 \times 32$-pixel squares called **patches** [documented].

### The Exact Formula
1. **Patch Grid Calculation**:
   $$\text{patches}_w = \left\lceil \frac{\text{width}}{32} \right\rceil, \quad \text{patches}_h = \left\lceil \frac{\text{height}}{32} \right\rceil$$
   $$\text{total\_patches} = \text{patches}_w \times \text{patches}_h$$

2. **Billable Token Calculation**:
   $$\text{image\_tokens} = \lceil \text{total\_patches} \times 1.2 \rceil$$
   where $1.2$ is the model-specific token multiplier for the GPT-5.x and GPT-6 families [documented].

### Deterministic Pre-Flight Estimator
Because the patch formula is fully documented, image token consumption can be calculated in code before issuing an API call:

```python
import math

def estimate_image_tokens(width: int, height: int, multiplier: float = 1.2) -> int:
    patches_w = math.ceil(width / 32)
    patches_h = math.ceil(height / 32)
    return math.ceil((patches_w * patches_h) * multiplier)
```

---

## 5. Detail Levels: `low`, `high`, and `original`

The `detail` parameter controls image downscaling and patch allocation:

- **`low`**: Downsamples the image to fit within a $512 \times 512$ bounding box.
  - Maximum grid: $16 \times 16 = 256$ patches.
  - Maximum token cost: $\lceil 256 \times 1.2 \rceil = 308$ tokens.
  - *Best for*: Rough layout classification, dominant color, landscape damage, broad orientation.
- **`high`**: Scales the image to fit within a $2048 \times 2048$ box, then divides it into $512 \times 512$ tiles, plus one low-resolution overview.
  - *Best for*: Signatures, medium-sized diagrams, stamp validation, visible scratches.
- **`original`**: Evaluates the image at its native dimensions without downscaling.
  - *Best for*: Reading small text, serial numbers, fine print in receipts.

---

## 6. The `low` Detail Trap Across Model Families
- **The Trap**: In older experimental models (e.g., `gpt-5.4`), `low` detail mode sometimes enlarged images smaller than $512 \times 512$ up to the bounding box, causing small images to cost *more* in `low` mode than in `original` mode [community report].
- **Current Behavior (`gpt-5.6` & `gpt-6-luna`)**: The bug was corrected. Images are capped at a $512 \times 512$ box without upscaling; `low` mode will never cost more than `high` mode [documented].
- **Rule**: For small crops ($< 512 \times 512$, e.g., a signature crop of $300 \times 120$), specify `detail: "original"`. It bypasses tiling overhead and costs fewer tokens than a full bounding box.

---

## 7. Visual Text Limitations & Detection-Based Cropping

OpenAI documents specific failure modes when reading text in images [documented]:
1. **Small Text**: Text occupying fewer than 20–30 vertical pixels is frequently misread or dropped.
2. **Rotated & Inverted Text**: Upside-down or steeply angled text suffers high error rates.
3. **Low Contrast**: Subtle watermarks or faint receipt print cause model hallucination or false negatives.

### The Detection-Based Cropping Solution
Never send a massive full-resolution document image with `detail: "original"` and hope the model spots a tiny serial number or signature.
- **Step 1 (Deterministic/Local Detector)**: Use lightweight computer vision (e.g., bounding-box detector, contour analysis, or layout parser) to identify the target region (e.g., signature block or receipt total).
- **Step 2 (Targeted Crop)**: Crop the region, normalize its orientation (rotate upright), and send only the high-resolution crop to Decisions API.
- **Step 3 (Deterministic Verification)**: If text extraction is required, use Structured Outputs or specialized OCR; use Decisions API only to confirm presence or visual match.

---

## 8. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Always convert images to base64 data URLs** | Hosted URLs (e.g., S3 or CDN links) cause immediate HTTP 400 failures on the Decisions API endpoint. | Sending `{"image_url": "https://s3.amazonaws.com/bucket/claim.jpg"}`. |
| **Never rasterize entire multi-page PDFs to images** | Converts thousands of text tokens into hundreds of thousands of image tokens, risking the 272k long-context cliff. | Converting a 100-page commercial lease into 100 PNGs to check for a termination clause. |
| **Always crop and upright small text before evaluation** | The model's vision backbone struggles with rotated or sub-patch text in large frames. | Passing an unrotated photo of a crumpled receipt and asking for fine line-item details. |
| **Use pre-flight token formulas instead of guessing costs** | Patch math is deterministic ($\lceil w/32 \rceil \times \lceil h/32 \rceil \times 1.2$), allowing exact cost estimation in code. | Running exploratory API calls on unmetered image batches to "see how much it costs". |
