class AIAnalysisService {
  constructor() {
    this.apiKey = null;
    this.apiEndpoint = 'https://api.anthropic.com/v1/messages';
  }

  async setApiKey(key) {
    this.apiKey = key;
  }

  async analyzeDOMElement(domAnalysis, context = {}) {
    if (!this.apiKey) {
      throw new Error('AI API key not configured');
    }

    const prompt = this.buildAnalysisPrompt(domAnalysis, context);
    
    try {
      const response = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.apiKey,
          'anthropic-version': '2023-06-01'
        },
        body: JSON.stringify({
          model: 'claude-3-haiku-20240307',
          max_tokens: 1000,
          messages: [{
            role: 'user',
            content: prompt
          }]
        })
      });

      if (!response.ok) {
        throw new Error(`AI API error: ${response.status}`);
      }

      const result = await response.json();
      return this.parseSleepyResponse(result.content[0].text);
      
    } catch (error) {
      console.error('AI analysis failed:', error);
      // Fallback to basic rule-based generation
      return this.basicFallback(domAnalysis);
    }
  }

  buildAnalysisPrompt(domAnalysis, context) {
    return `Analyze this web component and generate proper Sleepy syntax following the exact format shown in the examples.

SLEEPY SYNTAX FORMAT (from chat-encapsulated.sleepy):
- Semantic components: component$semantic-name
- Proper structure with parentheses: component$name: (content)
- Clean CSS styling: bg: #color, p: 4, rounded: lg (NO underscores/colons in values)
- Data binding: api.object.property, item.field
- Conditional logic: if: condition: [content], unless: condition: [content]
- Layouts: row: [elements], column: [elements]
- Events: onClick: function_name, onSubmit: handler

EXAMPLES FROM REFERENCE:
button$primary: (
  px: 4,
  py: 2,
  bg: #c96442,
  text: #fff,
  rounded: lg,
  hover-bg: #a55235,
  focus-ring: #c96442
): "Sign In"

card$product: (
  column: [
    img$product-image: api.product.image,
    h3: api.product.name,
    p: api.product.description,
    button$add-cart: "Add to Cart"
  ]
)

DOM ANALYSIS:
${JSON.stringify(domAnalysis, null, 2)}

CONTEXT:
- Page URL: ${context.url || 'unknown'}  
- Page title: ${context.pageTitle || 'unknown'}
- Page type: ${context.pageType || 'unknown'}
- Page domain: ${context.domain || 'unknown'}
- Surrounding elements: ${context.siblings ? JSON.stringify(context.siblings) : 'none'}
- Parent context: ${context.parent ? JSON.stringify(context.parent) : 'none'}

REQUIREMENTS:
1. Generate ONE clean component with semantic naming
2. Use proper Sleepy structure with parentheses and colons
3. Convert CSS classes to clean properties (no underscores/colons in values)
4. Infer data binding from content/context
5. Include layout structure (row/column) if appropriate
6. Add proper styling properties

Return ONLY the Sleepy component code in the correct format, nothing else.`;
  }

  parseSleepyResponse(aiResponse) {
    // Clean up the AI response and extract the Sleepy code
    let cleanCode = aiResponse.trim();
    
    // Remove markdown code blocks if present
    cleanCode = cleanCode.replace(/```[a-zA-Z]*\n?/g, '');
    cleanCode = cleanCode.replace(/```/g, '');
    
    // Remove any explanatory text before/after the code
    const lines = cleanCode.split('\n');
    let codeStart = -1;
    let codeEnd = -1;
    
    // Find the start of the component (line with $)
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes('$') && lines[i].includes(':')) {
        codeStart = i;
        break;
      }
    }
    
    // Find the end (last line with content)
    for (let i = lines.length - 1; i >= 0; i--) {
      if (lines[i].trim() && !lines[i].startsWith('//') && !lines[i].startsWith('Note:')) {
        codeEnd = i;
        break;
      }
    }
    
    if (codeStart >= 0 && codeEnd >= 0) {
      cleanCode = lines.slice(codeStart, codeEnd + 1).join('\n');
    }
    
    return {
      sleepyCode: cleanCode,
      confidence: 'ai-generated',
      reasoning: 'Generated using AI analysis with proper Sleepy syntax structure'
    };
  }

  basicFallback(domAnalysis) {
    // Generate proper Sleepy syntax as fallback
    const { tag, classes, id, textContent, attributes } = domAnalysis;
    
    // Generate semantic component name
    let componentName = this.generateSemanticName(tag, id, classes, textContent);
    
    // Convert CSS classes to proper Sleepy styling
    const styling = this.convertCSSToSleepy(classes);
    
    // Generate content/attributes
    const content = this.generateContent(tag, textContent, attributes);
    
    // Assemble proper Sleepy syntax
    let sleepyCode = `${componentName}`;
    
    if (styling.length > 0 || content) {
      sleepyCode += ': (';
      
      if (styling.length > 0) {
        sleepyCode += '\n  ' + styling.join(',\n  ');
      }
      
      if (content) {
        if (styling.length > 0) sleepyCode += ',\n  ';
        sleepyCode += content;
      }
      
      sleepyCode += '\n)';
    }

    return {
      sleepyCode,
      confidence: 'fallback',
      reasoning: 'AI analysis unavailable - generated using structured Sleepy syntax rules'
    };
  }

  generateSemanticName(tag, id, classes, textContent) {
    // Use ID if available and semantic
    if (id && !id.match(/^[a-f0-9-]+$/)) {
      return `${tag}$${id.replace(/[^a-zA-Z0-9]/g, '-')}`;
    }
    
    // Look for semantic classes
    const semanticClasses = classes.filter(c => 
      c.includes('button') || c.includes('card') || c.includes('nav') || 
      c.includes('header') || c.includes('footer') || c.includes('menu') ||
      c.includes('product') || c.includes('user') || c.includes('search')
    );
    
    if (semanticClasses.length > 0) {
      const semantic = semanticClasses[0]
        .replace(/btn|button/i, 'button')
        .replace(/[^a-zA-Z0-9]/g, '-')
        .toLowerCase();
      return `${tag}$${semantic}`;
    }
    
    // Use text content for buttons/links
    if ((tag === 'button' || tag === 'a') && textContent) {
      const name = textContent.toLowerCase()
        .replace(/[^a-zA-Z0-9\s]/g, '')
        .replace(/\s+/g, '-')
        .substring(0, 20);
      return `${tag}$${name}`;
    }
    
    // Generic component based on common patterns
    if (classes.some(c => c.includes('container') || c.includes('wrapper'))) {
      return `${tag}$container`;
    }
    
    return tag;
  }

  convertCSSToSleepy(classes) {
    const styling = [];
    
    for (const className of classes) {
      // Background colors
      if (className.startsWith('bg-')) {
        const color = className.replace('bg-', '').replace('-', '');
        if (color.match(/^\d+$/)) {
          styling.push(`bg: #${this.getTailwindColor(color)}`);
        } else {
          styling.push(`bg: ${color}`);
        }
      }
      
      // Text colors
      else if (className.startsWith('text-')) {
        const color = className.replace('text-', '');
        styling.push(`text: ${color}`);
      }
      
      // Padding
      else if (className.startsWith('p-')) {
        const value = className.replace('p-', '');
        styling.push(`p: ${value}`);
      }
      
      // Margin
      else if (className.startsWith('m-')) {
        const value = className.replace('m-', '');
        styling.push(`m: ${value}`);
      }
      
      // Border radius
      else if (className.includes('rounded')) {
        if (className === 'rounded') {
          styling.push('rounded: md');
        } else {
          const size = className.replace('rounded-', '');
          styling.push(`rounded: ${size}`);
        }
      }
      
      // Flexbox
      else if (className === 'flex') {
        styling.push('display: flex');
      } else if (className === 'flex-col') {
        styling.push('direction: column');
      }
      
      // Common utilities
      else if (className.includes('shadow')) {
        styling.push('shadow: md');
      }
    }
    
    return styling;
  }

  generateContent(tag, textContent, attributes) {
    if (textContent && textContent.length < 100) {
      return `content: "${textContent}"`;
    }
    
    if (attributes.href) {
      return `href: ${attributes.href}`;
    }
    
    if (attributes.src) {
      return `src: ${attributes.src}`;
    }
    
    return null;
  }

  getTailwindColor(number) {
    // Simple mapping for common Tailwind color numbers
    const colorMap = {
      '50': 'f9fafb', '100': 'f3f4f6', '200': 'e5e7eb',
      '300': 'd1d5db', '400': '9ca3af', '500': '6b7280',
      '600': '4b5563', '700': '374151', '800': '1f2937', '900': '111827'
    };
    return colorMap[number] || '6b7280';
  }

  // Get surrounding context for better AI analysis
  getSurroundingContext(element) {
    const context = {
      url: window.location.href,
      pageTitle: document.title,
      domain: window.location.hostname,
      pageType: this.inferPageType(),
      siblings: this.analyzeSiblings(element),
      parent: this.analyzeParent(element),
      pageDescription: this.getPageDescription()
    };

    return context;
  }

  inferPageType() {
    const url = window.location.href.toLowerCase();
    const title = document.title.toLowerCase();
    const body = document.body.textContent.toLowerCase();

    if (url.includes('shop') || url.includes('store') || 
        body.includes('add to cart') || body.includes('buy now')) {
      return 'ecommerce';
    }
    
    if (url.includes('blog') || document.querySelector('article')) {
      return 'blog';
    }
    
    if (url.includes('dashboard') || url.includes('admin')) {
      return 'dashboard';
    }

    if (document.querySelector('form[action*="login"]') || 
        document.querySelector('input[type="password"]')) {
      return 'auth';
    }

    return 'general';
  }

  analyzeSiblings(element) {
    const siblings = Array.from(element.parentElement?.children || [])
      .filter(el => el !== element)
      .slice(0, 3)
      .map(el => ({
        tag: el.tagName.toLowerCase(),
        classes: el.className.split(' ').filter(c => c).slice(0, 3),
        text: el.textContent?.trim().substring(0, 30) || null
      }));

    return siblings;
  }

  analyzeParent(element) {
    const parent = element.parentElement;
    if (!parent) return null;

    return {
      tag: parent.tagName.toLowerCase(),
      classes: parent.className.split(' ').filter(c => c).slice(0, 3),
      role: parent.getAttribute('role') || null
    };
  }

  getPageDescription() {
    // Try to get page description from meta tags
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) {
      return metaDesc.getAttribute('content').substring(0, 200);
    }

    // Fallback to first paragraph or heading
    const firstP = document.querySelector('p');
    const firstH1 = document.querySelector('h1');
    
    if (firstH1) {
      return firstH1.textContent.substring(0, 100);
    }
    
    if (firstP) {
      return firstP.textContent.substring(0, 150);
    }

    return null;
  }
}

// Export for use in content script
window.AIAnalysisService = AIAnalysisService;