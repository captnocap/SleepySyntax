class SleepySyntaxGenerator {
  constructor() {
    this.isActive = false;
    this.selectedElement = null;
    this.overlay = null;
    this.tooltip = null;
    this.aiService = new AIAnalysisService();
    this.resultsWindow = null;
    
    this.handleMouseOver = this.handleMouseOver.bind(this);
    this.handleMouseOut = this.handleMouseOut.bind(this);
    this.handleClick = this.handleClick.bind(this);
    this.handleKeyDown = this.handleKeyDown.bind(this);
    this.handleResultsMessage = this.handleResultsMessage.bind(this);
  }

  activate() {
    if (this.isActive) return;
    
    this.isActive = true;
    this.createOverlay();
    this.openResultsWindow();
    
    document.addEventListener('mouseover', this.handleMouseOver, true);
    document.addEventListener('mouseout', this.handleMouseOut, true);
    document.addEventListener('click', this.handleClick, true);
    document.addEventListener('keydown', this.handleKeyDown, true);
    window.addEventListener('message', this.handleResultsMessage, false);
    
    document.body.style.cursor = 'crosshair';
    console.log('Sleepy Syntax Generator activated');
  }

  deactivate() {
    if (!this.isActive) return;
    
    this.isActive = false;
    
    document.removeEventListener('mouseover', this.handleMouseOver, true);
    document.removeEventListener('mouseout', this.handleMouseOut, true);
    document.removeEventListener('click', this.handleClick, true);
    document.removeEventListener('keydown', this.handleKeyDown, true);
    window.removeEventListener('message', this.handleResultsMessage, false);
    
    this.clearHighlights();
    this.removeOverlay();
    
    document.body.style.cursor = '';
    console.log('Sleepy Syntax Generator deactivated');
  }

  createOverlay() {
    this.overlay = document.createElement('div');
    this.overlay.className = 'sleepy-overlay';
    document.body.appendChild(this.overlay);
    
    this.tooltip = document.createElement('div');
    this.tooltip.className = 'sleepy-tooltip';
    this.tooltip.style.display = 'none';
    document.body.appendChild(this.tooltip);
  }

  removeOverlay() {
    if (this.overlay) {
      this.overlay.remove();
      this.overlay = null;
    }
    if (this.tooltip) {
      this.tooltip.remove();
      this.tooltip = null;
    }
  }

  handleMouseOver(e) {
    if (!this.isActive) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    const element = e.target;
    if (element === this.overlay || element === this.tooltip) return;
    
    this.clearHighlights();
    element.classList.add('sleepy-highlight');
    
    this.showTooltip(element, e);
  }

  handleMouseOut(e) {
    if (!this.isActive) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    const element = e.target;
    element.classList.remove('sleepy-highlight');
    
    if (this.tooltip) {
      this.tooltip.style.display = 'none';
    }
  }

  handleClick(e) {
    if (!this.isActive) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    const element = e.target;
    if (element === this.overlay || element === this.tooltip) return;
    
    this.selectElement(element);
    this.deactivate();
  }

  handleKeyDown(e) {
    if (!this.isActive) return;
    
    if (e.key === 'Escape') {
      e.preventDefault();
      this.deactivate();
    }
  }

  async selectElement(element) {
    console.log('selectElement called with:', element);
    
    this.clearHighlights();
    this.selectedElement = element;
    element.classList.add('sleepy-selected');
    
    const analysis = this.analyzeDOMElement(element);
    const context = this.aiService.getSurroundingContext(element);
    
    console.log('Selected element:', element);
    console.log('Analysis:', analysis);
    console.log('Results window exists:', !!this.resultsWindow);
    console.log('Results window closed:', this.resultsWindow?.closed);
    
    // Send message to results window
    this.sendToResultsWindow({
      type: 'ELEMENT_SELECTED',
      data: {
        element: analysis,
        status: 'analyzing'
      }
    });
    
    try {
      // Use AI to generate better Sleepy syntax
      const aiResult = await this.aiService.analyzeDOMElement(analysis, context);
      
      console.log('AI Generated Sleepy code:', aiResult);
      
      // Send AI result to results window
      this.sendToResultsWindow({
        type: 'AI_ANALYSIS_COMPLETE',
        data: {
          element: analysis,
          aiResult: aiResult,
          status: 'complete'
        }
      });
      
    } catch (error) {
      console.error('AI analysis failed:', error);
      
      // Fallback to basic generation
      const fallbackCode = this.generateSleepyCode(analysis);
      this.sendToResultsWindow({
        type: 'AI_ANALYSIS_COMPLETE',
        data: {
          element: analysis,
          aiResult: {
            sleepyCode: fallbackCode,
            confidence: 'fallback',
            reasoning: 'AI unavailable - used basic rules'
          },
          status: 'fallback'
        }
      });
    }
  }

  showTooltip(element, mouseEvent) {
    if (!this.tooltip) return;
    
    const tagName = element.tagName.toLowerCase();
    const classes = element.className.split(' ').filter(c => c && !c.startsWith('sleepy-'));
    const id = element.id;
    
    let tooltipText = tagName;
    if (id) tooltipText += `#${id}`;
    if (classes.length > 0) tooltipText += `.${classes.slice(0, 2).join('.')}`;
    
    this.tooltip.textContent = tooltipText;
    this.tooltip.style.display = 'block';
    this.tooltip.style.left = mouseEvent.pageX + 10 + 'px';
    this.tooltip.style.top = mouseEvent.pageY - 30 + 'px';
  }

  clearHighlights() {
    document.querySelectorAll('.sleepy-highlight, .sleepy-selected').forEach(el => {
      el.classList.remove('sleepy-highlight', 'sleepy-selected');
    });
  }

  analyzeDOMElement(element) {
    const rect = element.getBoundingClientRect();
    
    return {
      tag: element.tagName.toLowerCase(),
      id: element.id || null,
      classes: element.className.split(' ').filter(c => c && !c.startsWith('sleepy-')),
      attributes: this.getAttributes(element),
      textContent: element.textContent?.trim().substring(0, 100) || null,
      children: this.analyzeChildren(element),
      position: {
        x: rect.left,
        y: rect.top,
        width: rect.width,
        height: rect.height
      },
      events: this.detectEventHandlers(element)
    };
  }

  getAttributes(element) {
    const attrs = {};
    for (const attr of element.attributes) {
      if (!attr.name.startsWith('sleepy-') && attr.name !== 'class') {
        attrs[attr.name] = attr.value;
      }
    }
    return attrs;
  }

  analyzeChildren(element) {
    return Array.from(element.children).slice(0, 5).map(child => ({
      tag: child.tagName.toLowerCase(),
      classes: child.className.split(' ').filter(c => c && !c.startsWith('sleepy-')),
      textContent: child.textContent?.trim().substring(0, 50) || null
    }));
  }

  detectEventHandlers(element) {
    const events = [];
    
    // Check for common event attributes
    ['onclick', 'onsubmit', 'onchange', 'oninput'].forEach(eventAttr => {
      if (element.hasAttribute(eventAttr)) {
        events.push({
          type: eventAttr.substring(2),
          handler: element.getAttribute(eventAttr)
        });
      }
    });
    
    return events;
  }

  generateSleepyCode(analysis) {
    const componentName = this.generateComponentName(analysis);
    const classes = this.convertCSSClasses(analysis.classes);
    const attributes = this.generateAttributes(analysis);
    const content = this.generateContent(analysis);
    
    let sleepyCode = componentName;
    
    if (classes) {
      sleepyCode += `:[${classes}]`;
    }
    
    if (attributes.length > 0) {
      sleepyCode += `:[${attributes.join(',')}]`;
    }
    
    if (content) {
      sleepyCode += `:${content}`;
    }
    
    return sleepyCode;
  }

  generateComponentName(analysis) {
    const { tag, id, classes, textContent } = analysis;
    
    // Use ID if available
    if (id) {
      return `${tag}$${id.replace(/[^a-zA-Z0-9]/g, '-')}`;
    }
    
    // Look for semantic classes
    const semanticClasses = classes.filter(c => 
      c.includes('button') || c.includes('card') || c.includes('nav') || 
      c.includes('header') || c.includes('footer') || c.includes('menu')
    );
    
    if (semanticClasses.length > 0) {
      const semantic = semanticClasses[0].replace(/[^a-zA-Z0-9]/g, '-');
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
    
    return tag;
  }

  convertCSSClasses(classes) {
    if (!classes || classes.length === 0) return '';
    
    // Convert Tailwind-style classes to Sleepy syntax
    return classes
      .filter(c => c && !c.startsWith('sleepy-'))
      .join('_')
      .replace(/-/g, ':');
  }

  generateAttributes(analysis) {
    const attributes = [];
    
    // Common attributes
    if (analysis.attributes.src) {
      attributes.push(`src:${analysis.attributes.src}`);
    }
    if (analysis.attributes.href) {
      attributes.push(`href:${analysis.attributes.href}`);
    }
    if (analysis.attributes.type) {
      attributes.push(`type:${analysis.attributes.type}`);
    }
    if (analysis.attributes.placeholder) {
      attributes.push(`placeholder:"${analysis.attributes.placeholder}"`);
    }
    
    // Event handlers
    analysis.events.forEach(event => {
      attributes.push(`on${event.type.charAt(0).toUpperCase() + event.type.slice(1)}:${event.handler}`);
    });
    
    return attributes;
  }

  generateContent(analysis) {
    if (!analysis.textContent) return null;
    
    // Simple text content
    if (analysis.children.length === 0) {
      return `"${analysis.textContent}"`;
    }
    
    return null;
  }

  openResultsWindow() {
    if (this.resultsWindow && !this.resultsWindow.closed) {
      this.resultsWindow.focus();
      return;
    }

    const extensionUrl = chrome.runtime.getURL('results.html');
    this.resultsWindow = window.open(
      extensionUrl,
      'sleepy-results',
      'width=450,height=600,scrollbars=no,resizable=yes,status=no,toolbar=no,menubar=no'
    );

    // Wait for the window to load before sending messages
    this.resultsWindow.addEventListener('load', () => {
      console.log('Results window loaded and ready');
    });
  }

  sendToResultsWindow(message) {
    if (this.resultsWindow && !this.resultsWindow.closed) {
      // Add delay to ensure window is fully loaded
      setTimeout(() => {
        console.log('Sending message to results window:', message);
        this.resultsWindow.postMessage(message, '*');
      }, 100);
    } else {
      console.warn('Results window not available for message:', message);
    }
  }

  handleResultsMessage(event) {
    if (event.source !== this.resultsWindow) return;

    const { type } = event.data;

    switch (type) {
      case 'ACTIVATE_PICKER_FROM_RESULTS':
        this.activate();
        break;
      case 'DEACTIVATE_PICKER_FROM_RESULTS':
        this.deactivate();
        break;
      case 'RESULTS_WINDOW_READY':
        console.log('Results window is ready');
        break;
    }
  }
}

// Initialize the generator
const sleepyGenerator = new SleepySyntaxGenerator();

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Content script received message:', message);
  
  if (message.type === 'ACTIVATE_PICKER') {
    console.log('Activating picker...');
    sleepyGenerator.activate();
    sendResponse({ success: true });
  } else if (message.type === 'DEACTIVATE_PICKER') {
    console.log('Deactivating picker...');
    sleepyGenerator.deactivate();
    sendResponse({ success: true });
  } else if (message.type === 'SET_API_KEY') {
    console.log('Setting API key...');
    sleepyGenerator.aiService.setApiKey(message.apiKey);
    sendResponse({ success: true });
  }
});

console.log('Sleepy Syntax content script loaded');