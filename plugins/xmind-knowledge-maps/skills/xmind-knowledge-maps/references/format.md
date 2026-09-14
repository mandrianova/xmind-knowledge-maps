# Modern Xmind workbook format

A current `.xmind` file is a ZIP archive. The leading `PK` bytes are the ZIP signature.

Essential entries:

- `content.json`: sheets, topic trees, theme, and relationships.
- `metadata.json`: format version and active sheet ID.
- `manifest.json`: packaged JSON files and resources.
- `resources/...`: embedded images, including formula previews.

The builder currently writes `dataStructureVersion: "3"` and
`layoutEngineVersion: "5"`, matching the native format saved by Xmind
26.05.01107. Keep these identifiers and the bundled template aligned whenever
Xmind performs another automatic workbook migration.

Topics recurse under `children.attached`. IDs must be unique. Use `branch: "folded"` for collapsed detail and `structureClass: "org.xmind.ui.map.clockwise"` for the house layout.

Xmind supports notes with both a plain fallback and formatted HTML:

```json
{"notes":{"plain":{"content":"Text"},"realHTML":{"content":"<p>Text</p>"}}}
```

The house style normally avoids notes. Use them only for exceptional bulky supporting material. Put ordinary explanations on the canvas and attach external URLs directly to source topics with `href`.

Code uses native multiline topic text with a per-topic monospace style and `customWidth`. This is deliberately text rather than an image: the user can select, copy, and edit it. Markdown fences remain literal characters in Xmind topics, so omit them.

An embedded PNG uses:

```json
{"image":{"src":"xap:resources/example.png","width":540,"height":280}}
```

A native formula keeps a rendered preview and editable LaTeX:

```json
{
  "title":"",
  "image":{"src":"xap:resources/formula.png","width":420,"height":80,"isMathJaxImage":true},
  "extensions":[{"provider":"org.xmind.ui.mathJax","content":{"content":"Q^*(s,a)=r+\\gamma\\max_b Q^*(s',b)"}}]
}
```

Relationships are sheet-level objects whose endpoints are topic IDs. Use a few visible lines and represent ordinary secondary references as linked topics.

The bundled theme and compact reference workbook contain no copied study content. They encode styling and representative mechanics only.
