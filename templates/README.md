# Blog Templates

This directory contains blog post templates that guide the LLM on how to structure articles.

## Available Templates

| Template | File | Use For |
|----------|------|---------|
| How-To | `how_to.md` | Step-by-step guides, tutorials |
| Comparison | `comparison.md` | Product comparisons, "X vs Y" articles |
| Definition | `definition.md` | Explanations, "What is X?" articles |
| Cost & ROI | `cost_roi.md` | Pricing, ROI analysis |
| Niche | `niche.md` | Market opportunities, niche ideas |

## How Templates Work

1. When the LLM generates content, it checks the topic's **pillar** field
2. The matching template is loaded and included in the prompt
3. The LLM follows the template structure for headings, sections, and formatting

## Customizing Templates

Edit any `.md` file to change how articles are generated:

```markdown
# My Custom Template

## Article Structure

### TL;DR
- Your instructions here

### Main Content
#### H2: Section Name
- What to include

### FAQ
- Question format guidelines
```

## Adding New Templates

1. Create a new `.md` file in this directory
2. Update the `pillar_to_file` mapping in `content_generator.py`:

```python
pillar_to_file = {
    "my-pillar": "my_template.md",
    # ... existing mappings
}
```

## Template Tips

- Be specific about heading structure
- Include examples of good formatting
- Specify number of items in lists
- Define FAQ question patterns
- Include SEO guidelines
