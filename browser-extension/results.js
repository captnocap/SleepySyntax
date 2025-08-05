class ResultsWindow {
  constructor() {
    this.isMinimized = false;
    this.currentResult = null;
    
    this.initializeElements();
    this.setupEventListeners();
    this.setupMessageListener();
    
    // Position window
    this.positionWindow();
  }

  initializeElements() {
    this.elements = {
      container: document.querySelector('.results-container'),
      statusMessage: document.getElementById('statusMessage'),
      codeOutput: document.getElementById('codeOutput'),
      copyBtn: document.getElementById('copyBtn'),
      newAnalysisBtn: document.getElementById('newAnalysisBtn'),
      reasoning: document.getElementById('reasoning'),
      reasoningText: document.getElementById('reasoningText'),
      confidenceBadge: document.getElementById('confidenceBadge'),
      elementInfo: document.getElementById('elementInfo'),
      elementDetails: document.getElementById('elementDetails'),
      minimizeBtn: document.getElementById('minimizeBtn'),
      closeBtn: document.getElementById('closeBtn')
    };
  }

  setupEventListeners() {
    this.elements.copyBtn.addEventListener('click', () => this.copyToClipboard());
    this.elements.newAnalysisBtn.addEventListener('click', () => this.startNewAnalysis());
    this.elements.minimizeBtn.addEventListener('click', () => this.toggleMinimize());
    this.elements.closeBtn.addEventListener('click', () => this.closeWindow());
    
    // Make window draggable by header
    this.makeDraggable();
  }

  setupMessageListener() {
    // Listen for messages from content script
    window.addEventListener('message', (event) => {
      console.log('Results window received message:', event.data);
      
      // Allow messages from any origin for extension communication
      const { type, data } = event.data;
      
      switch (type) {
        case 'ELEMENT_SELECTED':
          this.handleElementSelected(data);
          break;
        case 'AI_ANALYSIS_COMPLETE':
          this.handleAIAnalysisComplete(data);
          break;
        case 'ANALYSIS_ERROR':
          this.handleAnalysisError(data);
          break;
      }
    });
  }

  positionWindow() {
    // Position in bottom right corner
    document.body.style.position = 'fixed';
    document.body.style.bottom = '20px';
    document.body.style.right = '20px';
    document.body.style.width = '450px';
    document.body.style.height = '600px';
    document.body.style.zIndex = '999999';
    document.body.style.borderRadius = '12px';
    document.body.style.overflow = 'hidden';
    document.body.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.2)';
  }

  makeDraggable() {
    const header = document.querySelector('.header');
    let isDragging = false;
    let startX, startY, startLeft, startTop;

    header.addEventListener('mousedown', (e) => {
      if (e.target.closest('.btn-control')) return;
      
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      
      const rect = document.body.getBoundingClientRect();
      startLeft = rect.left;
      startTop = rect.top;
      
      header.style.cursor = 'grabbing';
    });

    document.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      
      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;
      
      document.body.style.left = (startLeft + deltaX) + 'px';
      document.body.style.top = (startTop + deltaY) + 'px';
    });

    document.addEventListener('mouseup', () => {
      isDragging = false;
      header.style.cursor = 'grab';
    });

    header.style.cursor = 'grab';
  }

  handleElementSelected(data) {
    this.showStatus('Analyzing element with AI...', 'analyzing');
    this.elements.codeOutput.textContent = 'AI is analyzing the selected element...';
    this.elements.copyBtn.disabled = true;
    this.elements.confidenceBadge.textContent = 'analyzing';
    this.elements.confidenceBadge.className = 'confidence-badge analyzing';
    
    // Show element details
    this.showElementDetails(data.element);
  }

  handleAIAnalysisComplete(data) {
    const { aiResult, status, element } = data;
    
    this.currentResult = aiResult;
    this.elements.codeOutput.textContent = aiResult.sleepyCode;
    this.elements.copyBtn.disabled = false;
    
    // Update confidence badge
    this.elements.confidenceBadge.textContent = aiResult.confidence;
    this.elements.confidenceBadge.className = `confidence-badge ${aiResult.confidence}`;
    
    // Show reasoning if available
    if (aiResult.reasoning) {
      this.elements.reasoningText.textContent = aiResult.reasoning;
      this.elements.reasoning.style.display = 'block';
    } else {
      this.elements.reasoning.style.display = 'none';
    }
    
    if (status === 'complete') {
      this.showStatus('✅ AI analysis complete!', 'complete');
    } else if (status === 'fallback') {
      this.showStatus('⚠️ AI unavailable - used fallback rules', 'error');
    }
    
    // Auto-minimize after showing result
    setTimeout(() => {
      if (!this.isMinimized) {
        this.showStatus('Analysis complete. Click to analyze another element.', 'ready');
      }
    }, 3000);
  }

  handleAnalysisError(data) {
    this.showStatus('❌ Analysis failed: ' + data.error, 'error');
    this.elements.codeOutput.textContent = 'Error occurred during analysis. Please try again.';
    this.elements.copyBtn.disabled = true;
  }

  showElementDetails(element) {
    const details = `Tag: ${element.tag}
Classes: ${element.classes.join(' ') || 'none'}
ID: ${element.id || 'none'}
Text: ${element.textContent ? element.textContent.substring(0, 50) + '...' : 'none'}`;
    
    this.elements.elementDetails.textContent = details;
    this.elements.elementInfo.style.display = 'block';
  }

  showStatus(message, type) {
    this.elements.statusMessage.textContent = message;
    this.elements.statusMessage.className = `status ${type}`;
  }

  async copyToClipboard() {
    if (!this.currentResult) return;
    
    try {
      await navigator.clipboard.writeText(this.currentResult.sleepyCode);
      
      const originalText = this.elements.copyBtn.textContent;
      this.elements.copyBtn.textContent = '✅ Copied!';
      this.elements.copyBtn.classList.add('copied');
      
      setTimeout(() => {
        this.elements.copyBtn.textContent = originalText;
        this.elements.copyBtn.classList.remove('copied');
      }, 2000);
      
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
      this.showStatus('Failed to copy to clipboard', 'error');
    }
  }

  startNewAnalysis() {
    // Send message to content script to activate picker
    window.parent.postMessage({
      type: 'ACTIVATE_PICKER_FROM_RESULTS'
    }, '*');
    
    this.showStatus('Element picker activated. Click any element on the page.', 'analyzing');
    this.elements.codeOutput.textContent = 'Click any element on the page to generate Sleepy syntax...';
    this.elements.copyBtn.disabled = true;
    this.elements.reasoning.style.display = 'none';
    this.elements.elementInfo.style.display = 'none';
    this.elements.confidenceBadge.textContent = 'waiting';
    this.elements.confidenceBadge.className = 'confidence-badge waiting';
  }

  toggleMinimize() {
    this.isMinimized = !this.isMinimized;
    
    if (this.isMinimized) {
      this.elements.container.classList.add('minimized');
      this.elements.minimizeBtn.textContent = '+';
      document.body.style.height = 'auto';
    } else {
      this.elements.container.classList.remove('minimized');
      this.elements.minimizeBtn.textContent = '−';
      document.body.style.height = '600px';
    }
  }

  closeWindow() {
    // Send message to content script to deactivate picker
    window.parent.postMessage({
      type: 'DEACTIVATE_PICKER_FROM_RESULTS'
    }, '*');
    
    window.close();
  }
}

// Initialize results window when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new ResultsWindow();
});

// Notify parent that results window is ready
window.parent.postMessage({
  type: 'RESULTS_WINDOW_READY'
}, '*');