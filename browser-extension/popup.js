class PopupController {
  constructor() {
    this.apiKey = null;
    
    this.initializeElements();
    this.loadStoredData();
    this.setupEventListeners();
  }

  initializeElements() {
    this.elements = {
      apiKeyInput: document.getElementById('apiKey'),
      saveApiKeyBtn: document.getElementById('saveApiKey'),
      statusText: document.getElementById('statusText')
    };
  }

  async loadStoredData() {
    try {
      const result = await chrome.storage.sync.get(['sleepyApiKey', 'pickerState', 'lastResult']);
      if (result.sleepyApiKey) {
        this.apiKey = result.sleepyApiKey;
        this.elements.apiKeyInput.value = '••••••••';
        this.elements.saveApiKeyBtn.textContent = 'Update API Key';
      }
      
      // Restore picker state
      if (result.pickerState === 'active') {
        this.isPickerActive = true;
        this.elements.activatePickerBtn.disabled = true;
        this.elements.deactivatePickerBtn.disabled = false;
        this.elements.activatePickerBtn.textContent = 'Picker Active - Click Element';
        this.showStatus('Element picker is active. Click any element on the page.', 'analyzing');
      }
      
      // Restore last result
      if (result.lastResult) {
        this.displayResult(result.lastResult);
      }
    } catch (error) {
      console.error('Failed to load stored data:', error);
    }
  }

  setupEventListeners() {
    this.elements.saveApiKeyBtn.addEventListener('click', () => this.saveApiKey());
    this.elements.activatePickerBtn.addEventListener('click', () => this.activatePicker());
    this.elements.deactivatePickerBtn.addEventListener('click', () => this.deactivatePicker());
    this.elements.copyBtn.addEventListener('click', () => this.copyToClipboard());
    
    // Clear placeholder when focusing API key input
    this.elements.apiKeyInput.addEventListener('focus', () => {
      if (this.elements.apiKeyInput.value === '••••••••') {
        this.elements.apiKeyInput.value = '';
        this.elements.apiKeyInput.type = 'text';
      }
    });
  }

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.type === 'ELEMENT_SELECTED') {
        this.handleElementSelected(message);
      } else if (message.type === 'AI_ANALYSIS_COMPLETE') {
        this.handleAIAnalysisComplete(message);
      }
    });
  }

  async saveApiKey() {
    const apiKey = this.elements.apiKeyInput.value.trim();
    
    if (!apiKey || apiKey === '••••••••') {
      this.showStatus('Please enter a valid API key', 'error');
      return;
    }

    if (!apiKey.startsWith('sk-ant-api')) {
      this.showStatus('Please enter a valid Claude API key (starts with sk-ant-api)', 'error');
      return;
    }

    try {
      // Store API key
      await chrome.storage.sync.set({ sleepyApiKey: apiKey });
      this.apiKey = apiKey;
      
      // Send to content script
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs[0]) {
        await chrome.tabs.sendMessage(tabs[0].id, {
          type: 'SET_API_KEY',
          apiKey: apiKey
        });
      }
      
      this.elements.apiKeyInput.value = '••••••••';
      this.elements.apiKeyInput.type = 'password';
      this.elements.saveApiKeyBtn.textContent = 'Update API Key';
      
      this.showStatus('API key saved successfully!', 'complete');
      setTimeout(() => this.hideStatus(), 2000);
      
    } catch (error) {
      console.error('Failed to save API key:', error);
      this.showStatus('Failed to save API key', 'error');
    }
  }

  async activatePicker() {
    if (!this.apiKey) {
      this.showStatus('Please configure your Claude API key first', 'error');
      return;
    }

    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tabs[0]) {
        this.showStatus('No active tab found', 'error');
        return;
      }

      this.currentTab = tabs[0];
      
      await chrome.tabs.sendMessage(this.currentTab.id, {
        type: 'ACTIVATE_PICKER'
      });
      
      this.isPickerActive = true;
      this.elements.activatePickerBtn.disabled = true;
      this.elements.deactivatePickerBtn.disabled = false;
      this.elements.activatePickerBtn.textContent = 'Picker Active - Click Element';
      
      // Store picker state
      await chrome.storage.sync.set({ pickerState: 'active' });
      
      this.showStatus('Element picker activated. Click any element on the page.', 'analyzing');
      
    } catch (error) {
      console.error('Failed to activate picker:', error);
      this.showStatus('Failed to activate picker. Please refresh the page.', 'error');
    }
  }

  async deactivatePicker() {
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs[0]) {
        await chrome.tabs.sendMessage(tabs[0].id, {
          type: 'DEACTIVATE_PICKER'
        });
      }
      
      this.isPickerActive = false;
      this.elements.activatePickerBtn.disabled = false;
      this.elements.deactivatePickerBtn.disabled = true;
      this.elements.activatePickerBtn.textContent = 'Start Element Selection';
      
      // Clear picker state
      await chrome.storage.sync.set({ pickerState: 'inactive' });
      
      this.hideStatus();
      
    } catch (error) {
      console.error('Failed to deactivate picker:', error);
    }
  }

  handleElementSelected(message) {
    this.showStatus('Analyzing element with AI...', 'analyzing');
    this.elements.codeOutput.textContent = message.sleepyCode;
    this.elements.copyBtn.classList.add('hidden');
    this.elements.reasoning.classList.add('hidden');
    this.elements.confidenceBadge.classList.add('hidden');
  }

  handleAIAnalysisComplete(message) {
    const { aiResult, status } = message;
    
    const result = {
      sleepyCode: aiResult.sleepyCode,
      confidence: aiResult.confidence,
      reasoning: aiResult.reasoning,
      status: status
    };
    
    this.displayResult(result);
    
    // Store result for persistence
    chrome.storage.sync.set({ lastResult: result });
    
    // Deactivate picker
    this.deactivatePicker();
  }

  displayResult(result) {
    this.elements.codeOutput.textContent = result.sleepyCode;
    this.elements.copyBtn.classList.remove('hidden');
    
    // Show confidence badge
    this.elements.confidenceBadge.textContent = result.confidence;
    this.elements.confidenceBadge.className = `confidence-badge confidence-${result.confidence}`;
    this.elements.confidenceBadge.classList.remove('hidden');
    
    // Show reasoning if available
    if (result.reasoning) {
      this.elements.reasoning.textContent = result.reasoning;
      this.elements.reasoning.classList.remove('hidden');
    }
    
    if (result.status === 'complete') {
      this.showStatus('AI analysis complete!', 'complete');
    } else if (result.status === 'fallback') {
      this.showStatus('AI unavailable - used basic rules', 'error');
    }
    
    // Auto-hide status after 3 seconds
    setTimeout(() => this.hideStatus(), 3000);
  }

  async copyToClipboard() {
    try {
      const code = this.elements.codeOutput.textContent;
      await navigator.clipboard.writeText(code);
      
      const originalText = this.elements.copyBtn.textContent;
      this.elements.copyBtn.textContent = 'Copied!';
      this.elements.copyBtn.style.background = '#059669';
      
      setTimeout(() => {
        this.elements.copyBtn.textContent = originalText;
        this.elements.copyBtn.style.background = '';
      }, 1000);
      
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
      this.showStatus('Failed to copy to clipboard', 'error');
    }
  }

  showStatus(message, type) {
    this.elements.statusMessage.textContent = message;
    this.elements.statusMessage.className = `status ${type}`;
    this.elements.statusMessage.classList.remove('hidden');
  }

  hideStatus() {
    this.elements.statusMessage.classList.add('hidden');
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new PopupController();
});