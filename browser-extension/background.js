// Background script for Sleepy Syntax Generator

let apiKey = null;

// Create context menu when extension is installed
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "generate-sleepy-syntax",
    title: "🤖 Generate Sleepy Syntax",
    contexts: ["all"]
  });
  
  console.log("Sleepy Syntax Generator context menu created");
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "generate-sleepy-syntax") {
    console.log("Context menu clicked on tab:", tab.id);
    console.log("Click info:", info);
    
    // Check if API key is configured
    const result = await chrome.storage.sync.get(['sleepyApiKey']);
    apiKey = result.sleepyApiKey;
    
    console.log("Retrieved API key:", apiKey ? "Present" : "Missing");
    
    if (!apiKey) {
      // Show notification to configure API key
      chrome.notifications.create({
        type: 'basic',
        iconUrl: '/icon-48.png',
        title: 'Sleepy Syntax Generator',
        message: 'Please configure your Claude API key in the extension popup first.'
      });
      return;
    }
    
    // Show starting notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: '/icon-48.png',
      title: 'Sleepy Syntax Generator',
      message: 'Starting analysis...'
    });
    
    // Inject and execute the element analysis
    try {
      console.log("Injecting script into tab:", tab.id);
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        function: analyzeClickedElement,
        args: [info]
      });
      console.log("Script injected successfully");
    } catch (error) {
      console.error('Failed to execute script:', error);
      chrome.notifications.create({
        type: 'basic',
        iconUrl: '/icon-48.png',
        title: 'Injection Failed',
        message: 'Could not analyze element: ' + error.message
      });
    }
  }
});

// Function that gets injected into the page
function analyzeClickedElement(info) {
  console.log('Analyzing element at coordinates:', info.pageX, info.pageY);
  
  // Find the element at the clicked coordinates
  const element = document.elementFromPoint(info.pageX, info.pageY);
  
  if (!element) {
    console.error('No element found at coordinates');
    return;
  }
  
  console.log('Found element:', element);
  
  // Create a simple highlight effect
  const originalOutline = element.style.outline;
  element.style.outline = '3px solid #3b82f6';
  
  // Analyze the element
  const analysis = {
    tag: element.tagName.toLowerCase(),
    id: element.id || null,
    classes: element.className.split(' ').filter(c => c),
    attributes: {},
    textContent: element.textContent?.trim().substring(0, 100) || null,
    position: {
      x: info.pageX,
      y: info.pageY
    }
  };
  
  // Get attributes
  for (const attr of element.attributes) {
    if (attr.name !== 'class') {
      analysis.attributes[attr.name] = attr.value;
    }
  }
  
  // Get page context
  const context = {
    url: window.location.href,
    title: document.title,
    domain: window.location.hostname
  };
  
  // Send analysis to background script
  chrome.runtime.sendMessage({
    type: 'ELEMENT_ANALYZED',
    analysis: analysis,
    context: context
  });
  
  // Remove highlight after 2 seconds
  setTimeout(() => {
    element.style.outline = originalOutline;
  }, 2000);
}

// Handle messages from content script
chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
  console.log('Background received message:', message);
  
  if (message.type === 'ELEMENT_ANALYZED') {
    console.log('Received element analysis:', message.analysis);
    
    // Show processing notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: '/icon-48.png',
      title: 'Sleepy Syntax Generator',
      message: 'Analyzing element with AI...'
    });
    
    try {
      console.log('Starting AI generation with API key:', apiKey ? 'Present' : 'Missing');
      
      // Generate Sleepy syntax using AI
      const sleepyCode = await generateSleepySyntax(message.analysis, message.context);
      console.log('Generated Sleepy code:', sleepyCode);
      
      // Create and download the .sleepy file
      await downloadSleepyFile(sleepyCode, message.analysis);
      console.log('File downloaded successfully');
      
      // Show success notification
      chrome.notifications.create({
        type: 'basic',
        iconUrl: '/icon-48.png',
        title: 'Sleepy Syntax Generated!',
        message: 'Downloaded as .sleepy file'
      });
      
    } catch (error) {
      console.error('Failed to generate Sleepy syntax:', error);
      
      // Show error notification
      chrome.notifications.create({
        type: 'basic',
        iconUrl: '/icon-48.png',
        title: 'Generation Failed',
        message: 'Error: ' + error.message
      });
    }
  }
  
  // Important: return true for async response
  return true;
});

// Generate Sleepy syntax using AI
async function generateSleepySyntax(analysis, context) {
  const prompt = buildAnalysisPrompt(analysis, context);
  console.log('AI Prompt:', prompt);
  
  try {
    console.log('Making API request to Anthropic...');
    console.log('API Key starts with:', apiKey ? apiKey.substring(0, 15) + '...' : 'None');
    
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
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

    console.log('API Response status:', response.status);
    console.log('API Response headers:', response.headers);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error response:', errorText);
      throw new Error(`AI API error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    console.log('API Response:', result);
    return cleanSleepyResponse(result.content[0].text);
    
  } catch (error) {
    console.error('AI analysis failed:', error);
    // Return fallback syntax
    console.log('Using fallback syntax generation');
    return generateFallbackSyntax(analysis);
  }
}

// Build the AI analysis prompt
function buildAnalysisPrompt(analysis, context) {
  return `Analyze this web element and generate proper Sleepy syntax.

SLEEPY SYNTAX FORMAT:
- Semantic components: component$semantic-name
- Structure: component$name: (properties)
- Clean styling: bg: #color, p: 4, rounded: lg
- Data binding: api.object.property, item.field
- Layouts: row: [elements], column: [elements]

ELEMENT ANALYSIS:
${JSON.stringify(analysis, null, 2)}

CONTEXT:
- URL: ${context.url}
- Title: ${context.title}
- Domain: ${context.domain}

Generate ONE clean Sleepy component with semantic naming and proper structure. Return ONLY the Sleepy code.`;
}

// Clean up AI response
function cleanSleepyResponse(aiResponse) {
  let cleanCode = aiResponse.trim();
  
  // Remove markdown code blocks
  cleanCode = cleanCode.replace(/```[a-zA-Z]*\n?/g, '');
  cleanCode = cleanCode.replace(/```/g, '');
  
  // Find the actual Sleepy code
  const lines = cleanCode.split('\n');
  let codeStart = -1;
  let codeEnd = -1;
  
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('$') && lines[i].includes(':')) {
      codeStart = i;
      break;
    }
  }
  
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].trim() && !lines[i].startsWith('//')) {
      codeEnd = i;
      break;
    }
  }
  
  if (codeStart >= 0 && codeEnd >= 0) {
    cleanCode = lines.slice(codeStart, codeEnd + 1).join('\n');
  }
  
  return cleanCode;
}

// Generate fallback syntax when AI fails
function generateFallbackSyntax(analysis) {
  const { tag, classes, id, textContent } = analysis;
  
  // Generate semantic name
  let componentName = tag;
  if (id && !id.match(/^[a-f0-9-]+$/)) {
    componentName = `${tag}$${id.replace(/[^a-zA-Z0-9]/g, '-')}`;
  } else if (textContent && (tag === 'button' || tag === 'a')) {
    const name = textContent.toLowerCase()
      .replace(/[^a-zA-Z0-9\s]/g, '')
      .replace(/\s+/g, '-')
      .substring(0, 20);
    componentName = `${tag}$${name}`;
  }
  
  // Basic styling from classes
  const styling = [];
  for (const className of classes) {
    if (className.startsWith('bg-')) {
      styling.push(`bg: ${className.replace('bg-', '')}`);
    } else if (className.startsWith('text-')) {
      styling.push(`text: ${className.replace('text-', '')}`);
    } else if (className.includes('rounded')) {
      styling.push('rounded: md');
    }
  }
  
  // Assemble code
  let sleepyCode = componentName;
  if (styling.length > 0 || textContent) {
    sleepyCode += ': (';
    if (styling.length > 0) {
      sleepyCode += '\n  ' + styling.join(',\n  ');
    }
    if (textContent) {
      if (styling.length > 0) sleepyCode += ',\n  ';
      sleepyCode += `content: "${textContent.substring(0, 50)}"`;
    }
    sleepyCode += '\n)';
  }
  
  return sleepyCode;
}

// Download the generated Sleepy code as a file
async function downloadSleepyFile(sleepyCode, analysis) {
  const filename = `${analysis.tag}-component-${Date.now()}.sleepy`;
  const content = `// Generated by Sleepy Syntax Generator
// Element: ${analysis.tag}${analysis.id ? '#' + analysis.id : ''}
// Classes: ${analysis.classes.join(' ') || 'none'}
// Generated: ${new Date().toISOString()}

${sleepyCode}
`;
  
  const blob = new Blob([content], { type: 'text/plain' });
  const blobUrl = URL.createObjectURL(blob);
  
  await chrome.downloads.download({
    url: blobUrl,
    filename: filename,
    saveAs: false
  });
  
  // Clean up the blob URL
  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}