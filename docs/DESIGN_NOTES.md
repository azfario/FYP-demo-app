# UI direction and decisions

Reading this as: a compact flood-segmentation workspace for portfolio reviewers, with the owner's space-control-panel direction, dark transparent surfaces and neon green hierarchy, dial ENERGY 2 / RHYTHM 1 / MOTION 1.

Antislop mode: during, selected by the owner in this conversation. The core filter is applied without installing optional companion skills or changing global agent instructions.

The space-dashboard brief replaces cream panels and the red action with dark green glass and neon green controls. The Hand Test addition keeps that direction and the existing background image byte-for-byte. The sample gallery remains absent; repository samples and APIs remain available. The original segmentation workflow and model remain unchanged; separate comparison endpoints accept an additional reference mask.

| Decision | Purpose |
| --- | --- |
| Generated satellite background | Follow the owner's explicit reference: one satellite silhouette, a natural star field, and amber/navy Milky Way colours. |
| Static image and 60% black overlay | Preserve the original scene while keeping header text readable over bright stars. |
| Dark green panels at 76% opacity | Keep the requested space image visible while protecting text contrast across the photograph. |
| `#7cffb2` headings and `#39ff88` primary action | Follow the owner's neon green direction and give segmentation the strongest control emphasis. |
| Self-hosted Inter | Use the reference's permitted open-source substitute for proprietary Pin Sans, with no runtime font network request. |
| One compact heading and two workspace columns | Give upload and results priority, with minimal prose and no separate marketing section. |
| 20 to 24px padding and gutters | Group controls, metrics and imagery without the former marketing-page spacing. |
| 12px controls and 24px panels | Give the dashboard a more compact frame without bulky pill shapes. |
| Blur on upload and results only | Express the requested glass treatment on the two active work areas; performance remains translucent without another blur layer. |
| Restrained title glow and primary hover glow | Establish space identity and action feedback without glowing every border, value and control. |
| One tinted shadow on results | Elevate the scientific image as the main workspace. |
| Natural square satellite previews | Preserve geography and raster proportions in every view. |
| Computational-only sidebar | Follow the owner's simplification: one Model computational performance heading and four values, without a historical accuracy table or small explanatory text. |
| DeepLab model label | Use the owner's requested short name in the header, comparison caption, image alt text and page title; retain D4 provenance in scientific metadata. |
| Four computational values | Show exact API parameter count and device, then measured inference and server processing times only after a real prediction. No estimated FPS, VRAM or FLOPs. |
| Blue overlay and explicit legend | Distinguish model output from natural-colour imagery; this is a data colour, not a second primary UI action. |
| Minimal motion | Indicate real processing and control state without distracting from image comparison. |
| One fixed dark appearance | Follow the owner's explicit space-dashboard brief without adding a theme toggle. |
| Text-only product identity | Use the project's name without inventing an unrequested logo or mascot. |
| Two workspace tabs | Keep reference-assisted evaluation separate from ordinary two-file inference, while retaining independent results. |
| Equal square comparison masks | Let reviewers inspect the same geographic extent at equal scale; stack on mobile for readability. |
| White/black/grey comparison legend | Use identical water, background and exclusion colours in both masks without inventing a decorative data palette. |
| Per-image scores immediately below masks | Tie each numerical claim to the actual uploaded reference and prediction, distinct from historical centre-crop scores. |
| Five wrapping view controls | Preserve the original imagery views while adding Compare without squeezing mobile touch targets. |
| Comparison images use nearest-neighbour display | Keep binary label boundaries sharp without changing raster pixels or model inference. |

The plus glyph opens folder selection. Controls retain their real functions, with keyboard focus, processing, success and error states. No sample navigation, signup, testimonials, fictional statistics, FAQ, or placeholder destinations are included. Historical metrics come from the selected checkpoint's recorded evaluation.

Runtime measurements are for the full 512 × 512 image processed as four 256 × 256 patches. Inference includes patch preparation, device transfer, model forward passes, sigmoid and copying probabilities to CPU. Thresholding follows this timer. Processing additionally covers validation, server preparation and export; neither includes network or browser rendering time. Timing values reset with the existing result lifecycle when clearing, changing folders or starting another prediction. The interface shows `Awaiting run` before a result and `Unavailable` for model facts if the service cannot be reached. Reduced-transparency preference uses an opaque dark surface, and reduced-motion preference disables animation.

Background SHA256 before redesign: `369dbce74276e08360f97298259ebb9fb9ad3f30b410a022b5b6aee105fac577`.

## Background provenance

Built-in imagegen tool, one newly generated opaque asset, 1672 × 941 pixels. Saved to `frontend/public/satellite-background.png` and bundled for offline use. The supplied `reference_fyp_web.jpg` was visual direction; the generated scene is decorative, not satellite input or a claimed photograph of a particular Sentinel spacecraft.

Final prompt:

> Create a high-resolution wide landscape (16:9) photographic-style website background. Visual direction: one black silhouette of an unbranded Earth-observation satellite with long rectangular solar panels and a dish antenna, against a dense natural star field and a diagonal Milky Way band. Deep navy and black space, subtle warm amber/brown starlight, restrained blue-violet nebula detail, matching the supplied user's satellite-and-space reference in mood. Place the satellite off-centre toward the upper left edge, so it remains visible around a centered web workspace; keep the central/right area less visually busy. The satellite should look like a distant instrument in orbit, not a fictional spaceship. Static realistic image only. No text, labels, logos, UI, borders, extra spacecraft, planets, artificial lens flare or graphic gradients. Deliver a polished raster background suitable for a flood segmentation application. Background opaque.
