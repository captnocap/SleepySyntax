"use strict";
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
exports.__esModule = true;
exports.deactivate = exports.activate = void 0;
var vscode = require("vscode");
function activate(context) {
    console.log('🌙 SleepySyntax Pro extension activated!');
    // Enhanced formatter with full-stack support
    var formatter = vscode.languages.registerDocumentFormattingEditProvider('sleepy', {
        provideDocumentFormattingEdits: function (document) {
            var text = document.getText();
            var formatted = formatSleepySyntaxPro(text);
            var range = new vscode.Range(document.positionAt(0), document.positionAt(text.length));
            return [vscode.TextEdit.replace(range, formatted)];
        }
    });
    // Semantic token provider for enhanced highlighting
    var tokenProvider = vscode.languages.registerDocumentSemanticTokensProvider('sleepy', new SleepySemanticTokenProvider(), new vscode.SemanticTokensLegend(['section', 'apiEndpoint', 'styleVariant', 'apiBinding', 'databaseField'], ['bold', 'italic', 'underline']));
    // Hover provider for documentation
    var hoverProvider = vscode.languages.registerHoverProvider('sleepy', {
        provideHover: function (document, position) {
            var wordRange = document.getWordRangeAtPosition(position);
            if (!wordRange)
                return;
            var word = document.getText(wordRange);
            var hover = getSleepySyntaxHover(word, document, position);
            if (hover) {
                return new vscode.Hover(hover);
            }
        }
    });
    // Auto-completion provider
    var completionProvider = vscode.languages.registerCompletionItemProvider('sleepy', {
        provideCompletionItems: function (document, position) {
            return getSleepySyntaxCompletions(document, position);
        }
    }, ':', ',', '.' // Trigger characters
    );
    // Structure analysis command
    var analyzeCommand = vscode.commands.registerCommand('sleepy.analyze', function () {
        var editor = vscode.window.activeTextEditor;
        if (editor && editor.document.languageId === 'sleepy') {
            var analysis = analyzeSleepySyntaxStructure(editor.document.getText());
            showStructureAnalysis(analysis);
        }
    });
    // Code lens provider for component references
    var codeLensProvider = vscode.languages.registerCodeLensProvider('sleepy', {
        provideCodeLenses: function (document) {
            return getSleepySyntaxCodeLenses(document);
        }
    });
    context.subscriptions.push(formatter, tokenProvider, hoverProvider, completionProvider, analyzeCommand, codeLensProvider);
}
exports.activate = activate;
var SleepySemanticTokenProvider = /** @class */ (function () {
    function SleepySemanticTokenProvider() {
    }
    SleepySemanticTokenProvider.prototype.provideDocumentSemanticTokens = function (document) {
        var builder = new vscode.SemanticTokensBuilder();
        var text = document.getText();
        // Enhanced semantic analysis
        this.analyzeSemanticTokens(text, builder);
        return builder.build();
    };
    SleepySemanticTokenProvider.prototype.analyzeSemanticTokens = function (text, builder) {
        var lines = text.split('\n');
        lines.forEach(function (line, lineIndex) {
            // Analyze sections
            var sectionMatch = line.match(/(styles|frontend|api|database|security|deployment):/);
            if (sectionMatch) {
                var startChar = line.indexOf(sectionMatch[1]);
                builder.push(lineIndex, startChar, sectionMatch[1].length, 0, 1); // section + bold
            }
            // Analyze API endpoints
            var apiMatch = line.match(/(GET|POST|PUT|DELETE|PATCH):([^:]+):/);
            if (apiMatch) {
                var methodStart = line.indexOf(apiMatch[1]);
                var pathStart = line.indexOf(apiMatch[2]);
                builder.push(lineIndex, methodStart, apiMatch[1].length, 1, 1); // apiEndpoint + bold
                builder.push(lineIndex, pathStart, apiMatch[2].length, 1, 2); // apiEndpoint + underline
            }
            // Analyze style variants
            var variantMatches = line.matchAll(/\$([a-zA-Z0-9_-]+)/g);
            for (var _i = 0, variantMatches_1 = variantMatches; _i < variantMatches_1.length; _i++) {
                var match = variantMatches_1[_i];
                var startChar = line.indexOf(match[0]);
                builder.push(lineIndex, startChar, match[0].length, 2, 0); // styleVariant
            }
            // Analyze API bindings
            var apiBindings = line.matchAll(/\b(api|item|response)\.[\w.]+/g);
            for (var _a = 0, apiBindings_1 = apiBindings; _a < apiBindings_1.length; _a++) {
                var match = apiBindings_1[_a];
                var startChar = line.indexOf(match[0]);
                builder.push(lineIndex, startChar, match[0].length, 3, 2); // apiBinding + italic
            }
        });
    };
    return SleepySemanticTokenProvider;
}());
function formatSleepySyntaxPro(text) {
    var formatted = '';
    var indent = 0;
    var inString = false;
    var currentSection = '';
    var _loop_1 = function (i) {
        var char = text[i];
        var nextChar = text[i + 1];
        // Skip whitespace in input (except in strings)
        if (char.match(/\s/) && !inString) {
            return "continue";
        }
        // Detect sections for special formatting
        if (char === '(' && ['styles', 'frontend', 'api', 'database', 'security', 'deployment'].some(function (s) {
            return text.substring(Math.max(0, i - 15), i).includes(s + ':');
        })) {
            currentSection = extractCurrentSection(text, i);
        }
        if (char === '{' || char === '(' || (char === '[' && nextChar !== ']')) {
            formatted += char;
            // Add section comments for major blocks
            if (char === '{' && currentSection) {
                formatted += " // ".concat(currentSection.toUpperCase(), " SECTION");
            }
            formatted += '\n' + '  '.repeat(++indent);
        }
        else if (char === '}' || char === ')' || (char === ']' && text[i - 1] !== '[')) {
            formatted = formatted.trimRight() + '\n' + '  '.repeat(--indent) + char;
            if (char === '}') {
                formatted += '\n'; // Extra line after major sections
            }
            if (nextChar && nextChar !== ',' && nextChar !== '}' && nextChar !== ')' && nextChar !== ']') {
                formatted += '\n' + '  '.repeat(indent);
            }
        }
        else if (char === ',' && !inString) {
            formatted += ',\n' + '  '.repeat(indent);
        }
        else if (char === ':' && !inString && nextChar !== '/') {
            formatted += ': ';
        }
        else {
            formatted += char;
        }
    };
    for (var i = 0; i < text.length; i++) {
        _loop_1(i);
    }
    // Clean up and add section separators
    return formatted
        .replace(/\n\s*\n/g, '\n')
        .replace(/^\s+|\s+$/g, '')
        .replace(/\n\s*([,\]\}\)])/g, '$1')
        .replace(/(\/\/ [A-Z]+ SECTION)/g, '\n$1\n');
}
function extractCurrentSection(text, position) {
    var beforePos = text.substring(Math.max(0, position - 20), position);
    var sections = ['styles', 'frontend', 'api', 'database', 'security', 'deployment'];
    for (var _i = 0, sections_1 = sections; _i < sections_1.length; _i++) {
        var section = sections_1[_i];
        if (beforePos.includes(section + ':')) {
            return section;
        }
    }
    return '';
}
function getSleepySyntaxHover(word, document, position) {
    var hoverDocs = {
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
    var hover = hoverDocs[word];
    if (hover) {
        return new vscode.MarkdownString(hover);
    }
    // API binding hover
    if (word.startsWith('api.')) {
        return new vscode.MarkdownString("\uD83D\uDCE1 **API Binding** - Dynamic data from `".concat(word, "`"));
    }
    // Style variant hover
    if (word.startsWith('$')) {
        return new vscode.MarkdownString("\uD83C\uDFA8 **Style Variant** - Applies `".concat(word, "` styling"));
    }
    return null;
}
function getSleepySyntaxCompletions(document, position) {
    var line = document.lineAt(position).text;
    var completions = [];
    // Section completions
    if (line.includes('{') && !line.includes(':')) {
        var sections = ['styles', 'frontend', 'api', 'database', 'security', 'deployment'];
        sections.forEach(function (section) {
            var item = new vscode.CompletionItem(section, vscode.CompletionItemKind.Module);
            item.detail = "".concat(section.charAt(0).toUpperCase() + section.slice(1), " Section");
            item.insertText = new vscode.SnippetString("".concat(section, ":(\n\t$0\n)"));
            completions.push(item);
        });
    }
    // UI component completions
    var uiComponents = ['card', 'button', 'input', 'column', 'row', 'h1', 'h2', 'h3', 'p', 'img'];
    uiComponents.forEach(function (comp) {
        var item = new vscode.CompletionItem(comp, vscode.CompletionItemKind.Class);
        item.detail = "UI Component";
        completions.push(item);
    });
    // Style variant completions after $
    if (line.includes('$')) {
        var variants = ['primary', 'secondary', 'ghost', 'dark', 'light', 'hover'];
        variants.forEach(function (variant) {
            var item = new vscode.CompletionItem(variant, vscode.CompletionItemKind.Color);
            item.detail = "Style Variant";
            completions.push(item);
        });
    }
    // API binding completions after api.
    if (line.includes('api.')) {
        var apiPaths = ['user.name', 'user.email', 'user.avatar', 'posts', 'auth.token'];
        apiPaths.forEach(function (path) {
            var item = new vscode.CompletionItem("api.".concat(path), vscode.CompletionItemKind.Variable);
            item.detail = "API Data Binding";
            completions.push(item);
        });
    }
    return completions;
}
function analyzeSleepySyntaxStructure(text) {
    // Basic structure analysis
    var analysis = {
        sections: [],
        apiEndpoints: 0,
        databaseTables: 0,
        uiComponents: 0,
        complexity: 'Simple'
    };
    // Count sections
    var sectionMatches = text.match(/(styles|frontend|api|database|security|deployment):/g);
    if (sectionMatches) {
        analysis.sections = __spreadArray([], new Set(sectionMatches.map(function (m) { return m.replace(':', ''); })), true);
    }
    // Count API endpoints
    analysis.apiEndpoints = (text.match(/(GET|POST|PUT|DELETE|PATCH):/g) || []).length;
    // Count database tables
    var dbMatches = text.match(/database:\([^)]*\)/g);
    if (dbMatches) {
        analysis.databaseTables = (dbMatches[0].match(/\w+:/g) || []).length - 1; // -1 for "database:"
    }
    // Count UI components
    analysis.uiComponents = (text.match(/\b(card|button|input|column|row|h[1-6]|p|img|div):/g) || []).length;
    // Determine complexity
    if (analysis.apiEndpoints > 10 || analysis.databaseTables > 5) {
        analysis.complexity = 'Enterprise';
    }
    else if (analysis.apiEndpoints > 5 || analysis.databaseTables > 2) {
        analysis.complexity = 'Complex';
    }
    else if (analysis.apiEndpoints > 0 || analysis.databaseTables > 0) {
        analysis.complexity = 'Moderate';
    }
    return analysis;
}
function showStructureAnalysis(analysis) {
    var message = "\n\uD83C\uDFD7\uFE0F SleepySyntax Structure Analysis\n\n\uD83D\uDCCA Sections: ".concat(analysis.sections.join(', '), "\n\uD83D\uDD0C API Endpoints: ").concat(analysis.apiEndpoints, "\n\uD83D\uDDC4\uFE0F Database Tables: ").concat(analysis.databaseTables, "\n\uD83C\uDFA8 UI Components: ").concat(analysis.uiComponents, "\n\u26A1 Complexity: ").concat(analysis.complexity, "\n    ");
    vscode.window.showInformationMessage('Structure Analysis Complete', 'View Details')
        .then(function (selection) {
        if (selection === 'View Details') {
            vscode.window.showInformationMessage(message.trim());
        }
    });
}
function getSleepySyntaxCodeLenses(document) {
    var lenses = [];
    var text = document.getText();
    var lines = text.split('\n');
    lines.forEach(function (line, index) {
        // Add code lens for major sections
        var sectionMatch = line.match(/(styles|frontend|api|database|security|deployment):/);
        if (sectionMatch) {
            var range = new vscode.Range(index, 0, index, line.length);
            var lens = new vscode.CodeLens(range);
            lens.command = {
                title: "\uD83D\uDCCA Analyze ".concat(sectionMatch[1], " section"),
                command: 'sleepy.analyze'
            };
            lenses.push(lens);
        }
    });
    return lenses;
}
function deactivate() {
    console.log('🌙 SleepySyntax Pro extension deactivated');
}
exports.deactivate = deactivate;
