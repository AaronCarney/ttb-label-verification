# T4 — OCR & Vision Architecture

**Phase:** 2 (Core Architecture)
**Status:** PARTIAL — general architecture questions ready; specifics gated on T1 (what to extract) and T2 (real label characteristics)
**Prerequisites:** T1, T2 for full depth
**Blocks:** T5, T6, T7

## Synopsis

The vision/OCR layer is responsible for extracting structured information from label images. Its outputs feed the rule engine (T3) and possibly the AI orchestration layer (T5). The brief flags difficult image conditions (angles, glare, low light) as a stretch goal but operationally important. Decision D-004 commits us to designing for production-parity, which means the OCR/vision layer must be substitutable from cloud to on-prem.

The unique challenge here: the government warning isn't just text — its formatting (caps, bold) is part of the rule. So we need not just OCR but visual analysis (typography detection, layout analysis).

## Required reading

- All five core artifacts (00 through 05)
- `T1-output.md` once available — to know exactly what fields/text we need to extract and what formatting properties matter
- `T2-output.md` once available — to know real label characteristics (resolution, format, common conditions)
- Survey reading: Tesseract, PaddleOCR, EasyOCR, Google Document AI, AWS Textract, Azure Document Intelligence, modern vision-language models (VLMs) for document understanding

## Output expected

A `T4-output.md` covering:

1. **Extraction requirements specification.** What text and visual features must be extracted, with confidence requirements per field.
2. **Approach recommendation.** Cloud OCR vs. self-hosted vs. VLM, with trade-offs.
3. **Preprocessing pipeline design.**
4. **Output format and confidence-scoring contract** to T3.
5. **Production-parity story:** how the layer is substituted for an on-prem variant.
6. **Edge case handling.** Unreadable images, partial occlusion, multilingual labels.

## In-topic questions

### Q4.1 — Extraction requirements specification
*Gated by T1 output.* For each field in the rule set, what does the vision layer need to extract?
- Plain text content
- Bounding region on the image
- Typographic properties (caps detection, bold/weight detection, font size estimation)
- Layout properties (which panel — front/back/side; spatial relationships)
- Color / contrast (for the "contrasting background" rule on the warning)

### Q4.2 — OCR approach trade-offs
Compare available OCR approaches for our use case:
- **Cloud OCR** (Google Document AI, AWS Textract, Azure Document Intelligence): accuracy, cost, latency, FedRAMP posture, ability to substitute with on-prem variants.
- **Self-hosted OCR** (Tesseract, PaddleOCR, EasyOCR): accuracy on label imagery specifically, deployment complexity, hardware needs.
- **Vision-language models** (Claude, GPT-4o, Gemini, open-source VLMs): can do extraction + reasoning in one pass; speed and cost implications; robustness on adversarial labels.
- **Hybrid:** OCR for text + VLM for layout reasoning.

Provide recommendation for the prototype and a clear path to the production variant.

### Q4.3 — Preprocessing pipeline
*Gated by Q4.2.* What preprocessing improves extraction quality on real labels?
- Deskewing
- Glare and reflection removal
- Contrast enhancement
- Background separation (label vs. bottle)
- Resolution upscaling
- Color normalization

For each: cost in latency vs. benefit in accuracy. What fits in the 5s SLA?

### Q4.4 — Typography and formatting detection
The "GOVERNMENT WARNING" formatting rule (caps + bold) is part of the validation. Standard OCR returns text but not always typographic properties. How do we reliably detect:
- All-caps rendering vs. just uppercase characters that happened to be input
- Bold weight vs. regular weight
- Continuous statement vs. broken layout
- Font size in physical units (mm) given image resolution metadata

### Q4.5 — Confidence-scoring contract
*Gated by Q4.2 and T3 Q3.5.* How does the vision layer express extraction confidence?
- Per-character / per-token / per-field
- How is confidence calibrated against ground truth?
- What's the contract between vision output and T3's confidence model?

### Q4.6 — Failure modes and "needs better photo" disposition
*Gated by Q4.3.* What are the vision layer's failure modes, and how are they surfaced?
- Image too low resolution
- Severe blur or glare that even preprocessing can't fix
- Label rotated past recoverable angle
- Partial occlusion
- Multiple labels in one image (front + back)

When does the layer report "cannot extract" rather than returning a low-confidence guess? This becomes a first-class disposition that the agent sees: "needs a better photo."

### Q4.7 — Multi-image handling
A single application can have front, back, and side labels — and the warning can appear on any of them. How does the layer handle multiple images per application?
- Cross-image deduplication and reconciliation
- "Where did this warning come from" provenance for the rule engine
- Performance budget for multi-image processing within 5s

### Q4.8 — Multilingual and non-English labels
Imports may have labels with non-English content (e.g., Tequila with Spanish-language elements). What's our scope here?
- Required for production but probably out of scope for prototype
- Even out-of-scope, what does graceful degradation look like?

### Q4.9 — Production-parity substitution story
*Gated by Q4.2.* If the prototype uses cloud OCR, what does the on-prem migration look like?
- Interface design that hides the implementation choice
- Quality gap between cloud and best-available on-prem (current state of art)
- Hardware requirements for on-prem option
- Phased migration possibilities (hybrid stays on cloud for some operations)

### Q4.10 — Real-world label characteristics
*Gated by T2 output, especially Q2.4.* From sampling the Public COLA Registry, what do real labels actually look like?
- Resolution distribution
- File format distribution
- Typical complexity (text density, decorative elements, special features like embossing)
- How many images per application (front/back/side breakdown)
- Edge cases (etched glass, clear acetate per Form 5100.31 instructions)

## Cross-topic synthesis questions
*(Held for later.)*

- **X-1 (T3+T4+T5+T6):** End-to-end time budget. Hold.
- **X-2 (T3+T4+T5):** Decision tree across components. Hold.
- **X-3 (T3+T4+T5+T7):** Production-readiness gaps. Hold.

## Notes for the researcher

- The most consequential choice in this topic is Q4.2 (OCR approach). Spend the most depth there.
- Q4.4 (typography detection) is unusual and underserved by standard OCR docs. Lean on VLM capabilities or specialized tooling here.
- Real-label data from T2 (Q4.10) is what separates a useful answer from a generic survey. Defer Q4.10 specifics if T2 isn't done, but flag it as outstanding.
- Don't over-engineer for the stretch-goal "handle any image quality" — Jenny said it might be out of scope. The defensible position is graceful degradation with a clear "needs better photo" output, not heroic recovery.
