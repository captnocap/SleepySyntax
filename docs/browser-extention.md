Sleepy Syntax Browser Extension - Actionable Plan

  Current Context Summary

  - Sleepy Syntax: AI-native declarative language for full-stack apps
  - CSS Structure: Uses underscores (bg-white_rounded-lg_shadow-md) and conditional
   classes (&active:[class:active])
  - Proven Compression: 60:1 to 140:1 ratios on real codebases (Open WebUI, Ollama)
  - Reference Examples: Located in /home/siah/sleepy/examples/ (verbose vs minimal
  patterns)

  Phase 1: Core Extension Foundation (Week 1-2)

  1.1 Extension Setup

  // manifest.json - Chrome extension basics
  {
    "name": "Sleepy Syntax Generator",
    "permissions": ["activeTab", "scripting"],
    "content_scripts": [{"matches": ["<all_urls>"]}]
  }

  1.2 Element Picker (Like DevTools)

  - Overlay injection: Highlight elements on hover
  - Click to select: Capture DOM element + children
  - Visual feedback: Show selected element boundaries

  1.3 DOM Analysis Engine

  function analyzeDOMElement(element) {
    return {
      tag: element.tagName,
      classes: element.className.split(' '),
      attributes: getAttributes(element),
      children: analyzeChildren(element),
      events: detectEventHandlers(element)
    }
  }

  Phase 2: CSS Class Translation (Week 2-3)

  2.1 Tailwind → Sleepy Converter

  Reference: /home/siah/sleepy/examples/*-verbose.sleepy for patterns
  // Convert: "bg-white rounded-lg shadow-md p-6"
  // To: "bg:white_rounded-lg_shadow-md_p-6"
  function convertCSSClasses(classes) {
    return classes.join('_').replace(/-/g, ':')
  }

  2.2 Conditional Class Detection

  Reference: Lines like &active:[class:active] in verbose examples
  - Detect :hover, :focus, :active states
  - Generate conditional syntax: &hover:[bg:blue-700]

  Phase 3: Component Structure Generation (Week 3-4)

  3.1 Semantic Naming

  Reference: Examples use $product, $cart-item, $user-menu naming
  function generateComponentName(element) {
    // Analyze classes, context, content to suggest semantic names
    // button.add-to-cart → button$add-to-cart
    // div.product-card → card$product
  }

  3.2 Hierarchy Mapping

  Reference: Nested structure in
  /home/siah/sleepy/examples/ecommerce-verbose.sleepy
  card$product:(
    img$product-image:[src:item.image],
    div$content:[
      h3:item.name,
      button$add-cart:[onClick:add_to_cart(item.id)]
    ]
  )

  Phase 4: Data Binding Inference (Week 4-5)

  4.1 Content Pattern Recognition

  // Detect patterns like:
  // "Product Name" → item.name
  // "$19.99" → format_currency(item.price)  
  // "5 reviews" → item.reviewCount + " reviews"

  4.2 Loop Detection

  Reference: forEach:api.products:[] patterns in examples
  - Detect repeated elements → forEach:api.items:[]
  - Identify data sources from context

  Phase 5: Interaction Mapping (Week 5-6)

  5.1 Event Handler Detection

  // Detect click handlers, form submissions
  // Generate: onClick:function_name(params)
  // Reference: Examples show onClick, onSubmit, onHover patterns

  5.2 Form Processing

  Reference: Search inputs, login forms in verbose examples
  - Input binding: value:api.search.query
  - Form submission: onSubmit:handle_form(data)

  Phase 6: Advanced Features (Week 6-8)

  6.1 API Integration Inference

  - Detect AJAX calls, fetch patterns
  - Generate API endpoint suggestions
  - Reference: api.products, api.user patterns in examples

  6.2 State Management

  - Identify dynamic content areas
  - Generate state variables and updates
  - Reference: Conditional rendering (if:, unless:) in examples

  Implementation Notes

  Key Reference Files:

  - Verbose Examples: /home/siah/sleepy/examples/*-verbose.sleepy
  - CSS Patterns: Look for underscore-separated classes
  - Component Names: Dollar sign notation ($component-name)
  - Conditional Logic: &state:[properties] pattern
  - Data Binding: api.object.property and item.field patterns

  Technical Stack:

  - Extension: Chrome Extension Manifest V3
  - DOM Analysis: Vanilla JavaScript
  - CSS Parsing: Custom parser for class extraction
  - Pattern Matching: Regex + semantic analysis
  - UI: Popup with generated code + copy button

  Success Metrics:

  - Accuracy: Generated Sleepy matches manual translation 80%+
  - Coverage: Handles 90% of common web patterns
  - Usability: One-click generation + copy to clipboard
  - Performance: Analysis completes in <2 seconds

  MVP Deliverable:

  Browser extension that can click any web element and generate basic Sleepy syntax
   with:
  - Proper CSS class conversion (underscores)
  - Semantic component naming
  - Basic data binding inference
  - Copy-to-clipboard functionality

  This would be the first tool to reverse-engineer web interfaces into AI-native
  syntax! 🚀
