import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    console.log('🌙 SleepySyntax Pro extension activated!');

    // Enhanced formatter with full-stack support
    const formatter = vscode.languages.registerDocumentFormattingEditProvider('sleepy', {
        provideDocumentFormattingEdits(document: vscode.TextDocument): vscode.TextEdit[] {
            const text = document.getText();
            const formatted = formatSleepySyntaxPro(text);
            const range = new vscode.Range(
                document.positionAt(0),
                document.positionAt(text.length)
            );
            return [vscode.TextEdit.replace(range, formatted)];
        }
    });

    // Semantic token provider for enhanced highlighting
    const tokenProvider = vscode.languages.registerDocumentSemanticTokensProvider(
        'sleepy',
        new SleepySemanticTokenProvider(),
        new vscode.SemanticTokensLegend(
            ['section', 'apiEndpoint', 'styleVariant', 'apiBinding', 'databaseField'],
            ['bold', 'italic', 'underline']
        )
    );

    // Hover provider for documentation
    const hoverProvider = vscode.languages.registerHoverProvider('sleepy', {
        provideHover(document, position) {
            const wordRange = document.getWordRangeAtPosition(position);
            if (!wordRange) return undefined;

            const word = document.getText(wordRange);
            const hover = getSleepySyntaxHover(word, document, position);
            
            if (hover) {
                return new vscode.Hover(hover);
            }
            return undefined;
        }
    });

    // Auto-completion provider
    const completionProvider = vscode.languages.registerCompletionItemProvider(
        'sleepy',
        {
            provideCompletionItems(document, position) {
                return getSleepySyntaxCompletions(document, position);
            }
        },
        ':', ',', '.'  // Trigger characters
    );

    // Format command
    const formatCommand = vscode.commands.registerCommand('sleepy.format', () => {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.languageId === 'sleepy') {
            const document = editor.document;
            const text = document.getText();
            const formatted = formatSleepySyntaxPro(text);
            
            const edit = new vscode.WorkspaceEdit();
            const range = new vscode.Range(
                document.positionAt(0),
                document.positionAt(text.length)
            );
            edit.replace(document.uri, range, formatted);
            vscode.workspace.applyEdit(edit);
        }
    });

    // Structure analysis command
    const analyzeCommand = vscode.commands.registerCommand('sleepy.analyze', () => {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.languageId === 'sleepy') {
            const analysis = analyzeSleepySyntaxStructure(editor.document.getText());
            showStructureAnalysis(analysis);
        }
    });

    // Code lens provider for component references
    const codeLensProvider = vscode.languages.registerCodeLensProvider('sleepy', {
        provideCodeLenses(document) {
            return getSleepySyntaxCodeLenses(document);
        }
    });

    context.subscriptions.push(
        formatter,
        tokenProvider,
        hoverProvider,
        completionProvider,
        formatCommand,
        analyzeCommand,
        codeLensProvider
    );
}

class SleepySemanticTokenProvider implements vscode.DocumentSemanticTokensProvider {
    provideDocumentSemanticTokens(document: vscode.TextDocument): vscode.SemanticTokens {
        const builder = new vscode.SemanticTokensBuilder();
        const text = document.getText();
        
        // Enhanced semantic analysis
        this.analyzeSemanticTokens(text, builder);
        
        return builder.build();
    }

    private analyzeSemanticTokens(text: string, builder: vscode.SemanticTokensBuilder) {
        const lines = text.split('\n');
        
        lines.forEach((line, lineIndex) => {
            // Analyze sections
            const sectionMatch = line.match(/(styles|frontend|api|database|security|deployment):/);
            if (sectionMatch) {
                const startChar = line.indexOf(sectionMatch[1]);
                builder.push(lineIndex, startChar, sectionMatch[1].length, 0, 1); // section + bold
            }

            // Analyze API endpoints
            const apiMatch = line.match(/(GET|POST|PUT|DELETE|PATCH):([^:]+):/);
            if (apiMatch) {
                const methodStart = line.indexOf(apiMatch[1]);
                const pathStart = line.indexOf(apiMatch[2]);
                builder.push(lineIndex, methodStart, apiMatch[1].length, 1, 1); // apiEndpoint + bold
                builder.push(lineIndex, pathStart, apiMatch[2].length, 1, 2); // apiEndpoint + underline
            }

            // Analyze style variants
            const variantMatches = line.matchAll(/\$([a-zA-Z0-9_-]+)/g);
            for (const match of variantMatches) {
                const startChar = line.indexOf(match[0]);
                builder.push(lineIndex, startChar, match[0].length, 2, 0); // styleVariant
            }

            // Analyze API bindings
            const apiBindings = line.matchAll(/\b(api|item|response)\.[\w.]+/g);
            for (const match of apiBindings) {
                const startChar = line.indexOf(match[0]);
                builder.push(lineIndex, startChar, match[0].length, 3, 2); // apiBinding + italic
            }
        });
    }
}

// Helper function to detect if we're inside a CSS value
function isInCSSValue(text: string, position: number): boolean {
    // Find the nearest : before this position
    let colonPos = -1;
    let i = position - 1;
    let parenthesesCount = 0;
    let bracketCount = 0;
    
    while (i >= 0) {
        const char = text[i];
        if (char === ')') parenthesesCount++;
        if (char === '(') parenthesesCount--;
        if (char === ']') bracketCount++;
        if (char === '[') bracketCount--;
        
        if (char === ':' && parenthesesCount === 0 && bracketCount === 0) {
            colonPos = i;
            break;
        }
        if (char === ',' && parenthesesCount === 0 && bracketCount === 0) {
            break; // Found a comma first, not in a CSS value
        }
        i--;
    }
    
    if (colonPos === -1) return false;
    
    // Check if the word before the colon is a CSS property
    const beforeColon = text.substring(0, colonPos).trim();
    const cssProperties = [
        'display', 'flexDirection', 'justifyContent', 'alignItems', 'padding', 'margin', 
        'width', 'height', 'backgroundColor', 'color', 'fontSize', 'borderRadius', 
        'border', 'boxShadow', 'position', 'zIndex', 'overflow', 'opacity', 'visibility'
    ];
    
    const lastWord = beforeColon.split(/\s+/).pop() || '';
    return cssProperties.includes(lastWord);
}

function formatSleepySyntaxPro(text: string): string {
    if (!text || text.trim().length === 0) {
        return text;
    }
    
    let formatted = '';
    let indent = 0;
    let i = 0;
    
    while (i < text.length) {
        const char = text[i];
        const nextChar = text[i + 1];
        
        // Skip whitespace, but preserve spaces in CSS values
        if (char.match(/\s/) && !isInCSSValue(text, i)) {
            i++;
            continue;
        }
        
        if (char === '{' || char === '(') {
            formatted += char + '\n' + '  '.repeat(++indent);
        } else if (char === '[') {
            // Check if this is an empty array []
            if (nextChar === ']') {
                formatted += '[]';
                i++; // Skip the closing ]
            } else {
                formatted += char + '\n' + '  '.repeat(++indent);
            }
        } else if (char === '}' || char === ')' || char === ']') {
            // Remove trailing whitespace and add proper indentation
            formatted = formatted.trimEnd();
            if (formatted.endsWith(',')) {
                formatted = formatted.slice(0, -1); // Remove trailing comma
            }
            formatted += '\n' + '  '.repeat(--indent) + char;
            
            // Add comma if there's more content after this closing bracket
            let nextNonSpace = i + 1;
            while (nextNonSpace < text.length && text[nextNonSpace].match(/\s/)) {
                nextNonSpace++;
            }
            if (nextNonSpace < text.length && text[nextNonSpace] === ',') {
                formatted += ',';
                i = nextNonSpace; // Skip to the comma
            }
            
            // Add newline if there's more content
            if (nextNonSpace < text.length && text[nextNonSpace] !== ',' && text[nextNonSpace] !== '}' && text[nextNonSpace] !== ')' && text[nextNonSpace] !== ']') {
                formatted += '\n' + '  '.repeat(indent);
            }
        } else if (char === ',') {
            formatted += ',\n' + '  '.repeat(indent);
        } else if (char === ':' && nextChar !== '/') {
            formatted += ': ';
        } else {
            formatted += char;
        }
        
        i++;
    }
    
    // Clean up the result
    return formatted
        .replace(/\n\s*\n/g, '\n') // Remove empty lines
        .replace(/^\s+|\s+$/g, '') // Trim start and end
        .replace(/,(\s*[}\]\)])/g, '$1'); // Remove trailing commas before closing brackets
}


function getSleepySyntaxHover(word: string, _document: vscode.TextDocument, _position: vscode.Position): vscode.MarkdownString | null {
    const hoverDocs: { [key: string]: string } = {
        'styles': '🎨 **Styles Section** - Define CSS-like styling for your components\n\nExample: `button:(px:4, py:2, bg:#3b82f6)`',
        'frontend': '💻 **Frontend Section** - Define your UI pages and components\n\nExample: `login:(column:[input, button])`',
        'api': '🔌 **API Section** - Define your backend endpoints and logic\n\nExample: `POST:/auth/login:(body:(email, password))`',
        'database': '🗄️ **Database Section** - Define your data schema and relationships\n\nExample: `users:(id:uuid_primary, name:string_required)`',
        'security': '🔒 **Security Section** - Configure authentication and security settings\n\nExample: `jwt:(secret:env.JWT_SECRET, expiry:24h)`',
        'deployment': '🚀 **Deployment Section** - Configure hosting and deployment settings\n\nExample: `frontend:(platform:vercel, build:npm_run_build)`',
        'forEach': '🔄 **ForEach Loop** - Iterate over API data arrays\n\nSyntax: `forEach:api.items:[template]`',
        'if': '❓ **Conditional Rendering** - Show content based on conditions\n\nSyntax: `if:api.condition:[content]`',
        'unless': '❌ **Negative Conditional** - Show content when condition is false\n\nSyntax: `unless:api.condition:[content]`'
    };

    const hover = hoverDocs[word];
    if (hover) {
        return new vscode.MarkdownString(hover);
    }

    // API binding hover
    if (word.startsWith('api.')) {
        return new vscode.MarkdownString(`📡 **API Binding** - Dynamic data from \`${word}\``);
    }

    // Style variant hover
    if (word.startsWith('$')) {
        return new vscode.MarkdownString(`🎨 **Style Variant** - Applies \`${word}\` styling`);
    }

    return null;
}

function getSleepySyntaxCompletions(document: vscode.TextDocument, position: vscode.Position): vscode.CompletionItem[] {
    const line = document.lineAt(position).text;
    const completions: vscode.CompletionItem[] = [];

    // Section completions
    if (line.includes('{') && !line.includes(':')) {
        const sections = ['styles', 'frontend', 'api', 'database', 'security', 'deployment'];
        sections.forEach(section => {
            const item = new vscode.CompletionItem(section, vscode.CompletionItemKind.Module);
            item.detail = `${section.charAt(0).toUpperCase() + section.slice(1)} Section`;
            item.insertText = new vscode.SnippetString(`${section}:(\n\t$0\n)`);
            completions.push(item);
        });
    }

    // UI component completions
    const uiComponents = ['card', 'button', 'input', 'column', 'row', 'h1', 'h2', 'h3', 'p', 'img'];
    uiComponents.forEach(comp => {
        const item = new vscode.CompletionItem(comp, vscode.CompletionItemKind.Class);
        item.detail = `UI Component`;
        completions.push(item);
    });

    // Style variant completions after $
    if (line.includes('$')) {
        const variants = ['primary', 'secondary', 'ghost', 'dark', 'light', 'hover'];
        variants.forEach(variant => {
            const item = new vscode.CompletionItem(variant, vscode.CompletionItemKind.Color);
            item.detail = `Style Variant`;
            completions.push(item);
        });
    }

    // API binding completions after api.
    if (line.includes('api.')) {
        const apiPaths = ['user.name', 'user.email', 'user.avatar', 'posts', 'auth.token'];
        apiPaths.forEach(path => {
            const item = new vscode.CompletionItem(`api.${path}`, vscode.CompletionItemKind.Variable);
            item.detail = `API Data Binding`;
            completions.push(item);
        });
    }

    return completions;
}

function analyzeSleepySyntaxStructure(text: string): any {
    // Basic structure analysis
    const analysis = {
        sections: [] as string[],
        apiEndpoints: 0,
        databaseTables: 0,
        uiComponents: 0,
        complexity: 'Simple'
    };

    // Count sections
    const sectionMatches = text.match(/(styles|frontend|api|database|security|deployment):/g);
    if (sectionMatches) {
        analysis.sections = [...new Set(sectionMatches.map(m => m.replace(':', '')))];
    }

    // Count API endpoints
    analysis.apiEndpoints = (text.match(/(GET|POST|PUT|DELETE|PATCH):/g) || []).length;

    // Count database tables
    const dbMatches = text.match(/database:\([^)]*\)/g);
    if (dbMatches) {
        analysis.databaseTables = (dbMatches[0].match(/\w+:/g) || []).length - 1; // -1 for "database:"
    }

    // Count UI components
    analysis.uiComponents = (text.match(/\b(card|button|input|column|row|h[1-6]|p|img|div):/g) || []).length;

    // Determine complexity
    if (analysis.apiEndpoints > 10 || analysis.databaseTables > 5) {
        analysis.complexity = 'Enterprise';
    } else if (analysis.apiEndpoints > 5 || analysis.databaseTables > 2) {
        analysis.complexity = 'Complex';
    } else if (analysis.apiEndpoints > 0 || analysis.databaseTables > 0) {
        analysis.complexity = 'Moderate';
    }

    return analysis;
}

function showStructureAnalysis(analysis: any) {
    const message = `
🏗️ SleepySyntax Structure Analysis

📊 Sections: ${analysis.sections.join(', ')}
🔌 API Endpoints: ${analysis.apiEndpoints}
🗄️ Database Tables: ${analysis.databaseTables}
🎨 UI Components: ${analysis.uiComponents}
⚡ Complexity: ${analysis.complexity}
    `;

    vscode.window.showInformationMessage('Structure Analysis Complete', 'View Details')
        .then(selection => {
            if (selection === 'View Details') {
                vscode.window.showInformationMessage(message.trim());
            }
        });
}

function getSleepySyntaxCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    const lenses: vscode.CodeLens[] = [];
    const text = document.getText();
    const lines = text.split('\n');

    lines.forEach((line, index) => {
        // Add code lens for major sections
        const sectionMatch = line.match(/(styles|frontend|api|database|security|deployment):/);
        if (sectionMatch) {
            const range = new vscode.Range(index, 0, index, line.length);
            const lens = new vscode.CodeLens(range);
            lens.command = {
                title: `📊 Analyze ${sectionMatch[1]} section`,
                command: 'sleepy.analyze'
            };
            lenses.push(lens);
        }
    });

    return lenses;
}

export function deactivate() {
    console.log('🌙 SleepySyntax Pro extension deactivated');
}