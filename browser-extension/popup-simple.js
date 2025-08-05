class SimplePopupController {
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
      const result = await chrome.storage.sync.get(['sleepyApiKey']);
      if (result.sleepyApiKey) {
        this.apiKey = result.sleepyApiKey;
        this.elements.apiKeyInput.value = '••••••••';
        this.elements.saveApiKeyBtn.textContent = 'Update API Key';
        this.elements.statusText.textContent = 'Ready to use - Right-click any element!';
        this.elements.statusText.style.color = '#10b981';
      } else {
        this.elements.statusText.textContent = 'Configure API key to get started';
        this.elements.statusText.style.color = '#f59e0b';
      }
    } catch (error) {
      console.error('Failed to load stored data:', error);
      this.elements.statusText.textContent = 'Error loading configuration';
      this.elements.statusText.style.color = '#ef4444';
    }
  }

  setupEventListeners() {
    this.elements.saveApiKeyBtn.addEventListener('click', () => this.saveApiKey());
    
    // Clear placeholder when focusing API key input
    this.elements.apiKeyInput.addEventListener('focus', () => {
      if (this.elements.apiKeyInput.value === '••••••••') {
        this.elements.apiKeyInput.value = '';
        this.elements.apiKeyInput.type = 'text';
      }
    });
  }

  async saveApiKey() {
    const apiKey = this.elements.apiKeyInput.value.trim();
    
    if (!apiKey || apiKey === '••••••••') {
      this.showStatus('Please enter a valid API key', '#ef4444');
      return;
    }

    if (!apiKey.startsWith('sk-ant-api')) {
      this.showStatus('Please enter a valid Claude API key (starts with sk-ant-api)', '#ef4444');
      return;
    }

    try {
      // Store API key
      await chrome.storage.sync.set({ sleepyApiKey: apiKey });
      this.apiKey = apiKey;
      
      this.elements.apiKeyInput.value = '••••••••';
      this.elements.apiKeyInput.type = 'password';
      this.elements.saveApiKeyBtn.textContent = 'Update API Key';
      
      this.showStatus('API key saved! Right-click any element to generate Sleepy syntax.', '#10b981');
      
    } catch (error) {
      console.error('Failed to save API key:', error);
      this.showStatus('Failed to save API key', '#ef4444');
    }
  }

  showStatus(message, color) {
    this.elements.statusText.textContent = message;
    this.elements.statusText.style.color = color;
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new SimplePopupController();
});