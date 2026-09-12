# Map specification

`build_xmind.py` accepts UTF-8 JSON. Relative paths resolve from the specification file.

```json
{
  "title": "Artificial Intelligence",
  "sheet_title": "Knowledge Map",
  "fold_depth": 3,
  "topics": [
    {
      "key": "rl",
      "title": "Reinforcement Learning",
      "children": [
        {"title": "An agent learns from rewards"},
        {"title": "Primary paper ↗", "href": "https://example.org/paper"},
        {"title": "Copyable code", "children": [{"code": "action = max(q_values)", "width": 560}]},
        {"title": "Interaction loop", "image": "diagrams/rl.png", "image_width": 560},
        {"key": "return", "formula": "G_t=\\sum_{k=0}^{T-t-1}\\gamma^k r_{t+k+1}"}
      ]
    }
  ],
  "relationships": [
    {"from": "rl", "to": "return", "label": "optimises expected"}
  ]
}
```

Required fields are `title` and `topics`. Each topic has exactly one of `title`, `formula`, or `code`. A `key` is needed for relationship endpoints. `href` makes a topic a clickable external link. `folded` overrides automatic folding at `fold_depth`.

Prefer visible child topics over `notes`. Reserve `notes` or `notes_html` for unusually bulky supporting material that would make the canvas unreadable; do not insert untrusted HTML. For sources, normally create a short child topic with `href`. Use the `sources` array only when hidden note content is explicitly wanted.

Images may be PNG, JPEG, or GIF; prefer PNG for diagrams and text. `image_width` controls display width while preserving aspect ratio.

For formulas, provide LaTeX without `$...$`. Rendering requires `pdflatex` and `pdftoppm`. If they are unavailable, create the native formula through Xmind UI or report the missing renderer; do not silently degrade it to plain text.

`caption` is optional native text below a formula image; it is not a note. Keep `formula` as the content field and use `caption`, not `title`, for its explanation. Put each variable in its own child formula topic. For example:

```json
{
  "formula": "z=\\sum_i w_i x_i+b,\\qquad y=f(z)",
  "caption": "Artificial neuron: weighted sum followed by activation",
  "children": [
    {"formula": "x_i", "caption": "Input feature at this index."},
    {"formula": "w_i", "caption": "Learned weight multiplying this input feature."},
    {"formula": "i", "caption": "Index identifying an input and its matching weight."},
    {"formula": "b", "caption": "Bias: learned offset added to the sum."},
    {"formula": "z", "caption": "Weighted sum plus bias, before activation."},
    {"formula": "f", "caption": "Activation function applied to the sum."},
    {"formula": "y", "caption": "Neuron output after activation."},
    {"title": "Example: inputs [2,1], weights [3,-1] and bias 0.5 give a pre-activation value of 5.5."}
  ]
}
```

The caption remains editable and copyable as topic text; the formula remains editable through Xmind's native MathJax extension. `width` optionally controls captioned-topic width (default 380). Use caption language appropriate to the map. Do not collapse the separate variable definitions into a prose list with raw underscores or caret notation.

Use `code` for a short multiline code block. The builder stores it as native topic text with a monospace style and a generous 560 px default width, so it remains editable, selectable, and copyable. Override that width with the numeric `width` field when needed. Do not add Markdown fences: Xmind topic text does not render fenced Markdown as a code block. Put the language or purpose in a small parent topic. Split long listings into logical blocks rather than creating an enormous topic.

The bundled theme is used unless `theme_file` points to another exported theme JSON.
