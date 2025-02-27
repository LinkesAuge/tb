# Template Matching Workflow

## Overview

Template matching is a core functionality in TB Scout that enables the application to identify game elements by comparing them with pre-defined template images. This document describes the complete workflow of template matching, from template preparation to result visualization.

## Workflow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Capture Screen │────►│ Process Image   │────►│ Load Templates  │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         │                                               ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│ Display Results │◄────│ Filter Results  │◄────│ Match Templates │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Step-by-Step Process

### 1. Screen Capture

The template matching process begins with capturing the current state of the game window:

```python
# Capture the game window
screenshot = capture_manager.capture_active_window()
```

Key components involved:
- `CaptureManager`: Manages the screen capture process
- `WindowInterface`: Provides information about the game window

The captured screenshot is returned as a NumPy array in BGR format (OpenCV's default format).

### 2. Image Processing

Before template matching, the screenshot may undergo preprocessing to improve matching accuracy:

```python
# Preprocess the screenshot
processed_image = template_matcher.preprocess_image(screenshot)
```

Common preprocessing steps include:
- Grayscale conversion (for templates that don't rely on color)
- Resizing (to handle different game resolutions)
- Noise reduction
- Contrast enhancement
- Region of interest (ROI) selection

### 3. Template Loading

Templates are loaded from the template directory based on the requested template names:

```python
# Load templates
templates = template_matcher.load_templates(["button_ok", "button_cancel"])
```

Templates are stored in the `patterns/` directory, organized by category:
- `patterns/buttons/`: Button templates
- `patterns/resources/`: Resource icons
- `patterns/buildings/`: Building icons
- etc.

Each template includes:
- Template image
- Metadata (JSON file) with:
  - Description
  - Category
  - Default threshold
  - Anchor points
  - Mask (optional)

### 4. Template Matching

The core matching process compares each template against the screenshot:

```python
# Perform template matching
results = template_matcher.find_templates(
    screenshot, 
    templates, 
    threshold=0.8,
    limit=5
)
```

The matching process:
1. For each template:
   - Apply the template matching algorithm (cv2.matchTemplate)
   - Use the specified method (TM_CCOEFF_NORMED, TM_SQDIFF_NORMED, etc.)
   - Apply a threshold to filter low-confidence matches
   - Apply non-maximum suppression to avoid duplicate detections
2. Collect all matches above the threshold
3. Sort matches by confidence score

### 5. Result Filtering

The raw matching results may be filtered based on various criteria:

```python
# Filter results
filtered_results = template_matcher.filter_results(
    results,
    min_confidence=0.85,
    region=(100, 100, 400, 300),
    max_results=3
)
```

Filtering options include:
- Minimum confidence threshold
- Region of interest
- Maximum number of results
- Minimum distance between matches
- Exclusion zones

### 6. Result Visualization

The final step is to visualize the matching results on the overlay:

```python
# Display results on overlay
for result in filtered_results:
    overlay.add_rectangle(
        x=result.x,
        y=result.y,
        width=result.width,
        height=result.height,
        color=(0, 255, 0),
        thickness=2,
        text=f"{result.template_name}: {result.confidence:.2f}"
    )
```

Visualization options include:
- Bounding boxes
- Confidence scores
- Template names
- Anchor points
- Heat maps

## Template Creation Process

### Capturing Templates

Templates can be created directly from the game using the template capture tool:

1. Open the Debug Window
2. Navigate to the Template Capture tab
3. Position the game to show the element you want to capture
4. Draw a selection rectangle around the element
5. Enter metadata (name, category, description)
6. Save the template

### Manual Template Creation

Templates can also be created manually:

1. Take a screenshot of the game
2. Crop the desired element using an image editor
3. Save the image in PNG format in the appropriate template directory
4. Create a JSON metadata file with the same name

Example metadata file (`button_ok.json`):
```json
{
    "name": "button_ok",
    "description": "OK confirmation button",
    "category": "buttons",
    "threshold": 0.8,
    "anchor_points": [
        {"name": "center", "x": 25, "y": 15},
        {"name": "text", "x": 25, "y": 10}
    ]
}
```

## Template Matching Configuration

Template matching behavior can be configured through the settings:

```json
{
    "template_matching": {
        "default_method": "cv2.TM_CCOEFF_NORMED",
        "default_threshold": 0.8,
        "use_grayscale": true,
        "enable_scaling": true,
        "scale_range": [0.9, 1.1],
        "scale_steps": 5,
        "enable_rotation": false,
        "max_results_per_template": 10,
        "non_max_suppression_threshold": 0.2
    }
}
```

## Advanced Features

### Multi-Scale Template Matching

For handling elements that may appear at different sizes:

```python
# Perform multi-scale template matching
results = template_matcher.find_templates_multi_scale(
    screenshot,
    templates,
    scale_range=(0.8, 1.2),
    scale_steps=5
)
```

### Template Matching with Masks

For templates with transparent or variable regions:

```python
# Load template with mask
template = template_matcher.load_template("button_with_text", use_mask=True)

# Perform template matching with mask
results = template_matcher.find_template(screenshot, template)
```

The mask defines which parts of the template should be considered during matching.

### Template Anchors

Templates can define anchor points for precise interaction:

```python
# Get anchor point for a match
anchor = template_matcher.get_anchor_point(match, "click_point")

# Click on the anchor point
game_actions.click(anchor.x, anchor.y)
```

Common anchor points include:
- Center
- Top-left
- Click points
- Text regions

### Template Groups

Templates can be organized into groups for batch processing:

```python
# Find any template from a group
results = template_matcher.find_template_group(
    screenshot,
    "resource_icons"
)
```

## Integration with Automation

Template matching is commonly used in automation sequences:

```json
{
    "type": "find_template",
    "template": "button_ok",
    "variable": "ok_button",
    "threshold": 0.85,
    "description": "Find OK button"
},
{
    "type": "if",
    "condition": "ok_button != None",
    "then": [
        {
            "type": "click_template",
            "template_result": "ok_button",
            "anchor": "center",
            "description": "Click OK button"
        }
    ]
}
```

## Troubleshooting

### Common Issues

1. **Low Confidence Matches**
   - Ensure the template is clear and distinctive
   - Adjust the threshold
   - Try different matching methods
   - Consider preprocessing the image

2. **No Matches Found**
   - Verify the template exists and is loaded correctly
   - Check if the element is visible on screen
   - Try lowering the threshold
   - Check if the game appearance has changed

3. **Multiple False Positives**
   - Make the template more specific
   - Increase the threshold
   - Use a mask to focus on distinctive features
   - Specify a more precise region of interest

### Debugging Tools

The Debug Window provides tools for troubleshooting template matching:

1. **Template Viewer**
   - View all available templates
   - See template metadata
   - Test templates against current screenshot

2. **Match Visualizer**
   - See all matches with confidence scores
   - View the matching heatmap
   - Adjust thresholds in real-time

3. **Template Tester**
   - Test individual templates
   - Try different matching methods
   - Adjust parameters and see results immediately

## Performance Considerations

Template matching can be computationally intensive. Consider these optimizations:

1. **Limit the Search Region**
   - Specify a region of interest when possible
   - Use game knowledge to focus on relevant areas

2. **Optimize Template Size**
   - Smaller templates match faster
   - Remove unnecessary background

3. **Use Appropriate Methods**
   - TM_CCOEFF_NORMED is generally a good balance
   - TM_SQDIFF_NORMED may be faster in some cases

4. **Batch Processing**
   - Process multiple templates in one pass
   - Reuse the same screenshot for multiple matches

5. **Resolution Considerations**
   - Match at a lower resolution when possible
   - Create templates at the most common resolution

## Best Practices

1. **Template Design**
   - Create templates with distinctive features
   - Avoid templates with too much background
   - Include enough context for reliable matching
   - Create multiple variants for variable elements

2. **Threshold Selection**
   - Start with a high threshold (0.8-0.9)
   - Adjust based on testing
   - Document optimal thresholds for each template

3. **Maintenance**
   - Update templates when game appearance changes
   - Organize templates in logical categories
   - Document template purpose and usage
   - Version control templates alongside code

4. **Testing**
   - Test templates against various screenshots
   - Verify templates work in different game states
   - Create automated tests for critical templates