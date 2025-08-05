#!/usr/bin/env python3
"""
SleepySyntax Parser - Written in SleepySyntax
Because why use regular code when you can use the notation that lets you sleep at night? 🌙
"""

# {sleepy_parser_program:(
#   imports:(
#     standard:[re, json, typing],
#     from_typing:[Dict, List, Optional, Union],
#     from_dataclasses:[dataclass, field],
#     from_enum:[Enum]
#   ),
#   
#   data_structures:(
#     TokenType:(
#       OPEN_BRACE:"OPEN_BRACE",
#       CLOSE_BRACE:"CLOSE_BRACE", 
#       OPEN_PAREN:"OPEN_PAREN",
#       CLOSE_PAREN:"CLOSE_PAREN",
#       OPEN_BRACKET:"OPEN_BRACKET",
#       CLOSE_BRACKET:"CLOSE_BRACKET",
#       COLON:"COLON",
#       COMMA:"COMMA",
#       IDENTIFIER:"IDENTIFIER",
#       API_BINDING:"API_BINDING",
#       STYLE_VARIANT:"STYLE_VARIANT",
#       EOF:"EOF"
#     ),
#     
#     Token:(
#       type:TokenType,
#       value:str,
#       position:int
#     ),
#     
#     SleepyNode:(
#       node_type:str,
#       name:Optional[str],
#       children:List[SleepyNode],
#       attributes:Dict[str, str],
#       api_binding:Optional[str],
#       style_variant:Optional[str]
#     )
#   ),
#   
#   lexer_service:(
#     class:SleepyLexer,
#     methods:(
#       __init__:(input:text:str),
#       tokenize:(returns:List[Token]),
#       _current_char:(returns:Optional[str]),
#       _peek_char:(returns:Optional[str]),
#       _advance:(),
#       _skip_whitespace:(),
#       _read_identifier:(returns:str),
#       _read_api_binding:(returns:str)
#     )
#   ),
#   
#   parser_service:(
#     class:SleepyParser,
#     methods:(
#       __init__:(tokens:List[Token]),
#       parse:(returns:SleepyNode),
#       _current_token:(returns:Optional[Token]),
#       _advance:(),
#       _parse_component:(returns:SleepyNode),
#       _parse_children:(returns:List[SleepyNode]),
#       _parse_attributes:(returns:Dict[str, str])
#     )
#   ),
#   
#   renderer_service:(
#     class:SleepyRenderer,
#     methods:(
#       __init__:(api_data:Dict),
#       render_to_html:(node:SleepyNode, returns:str),
#       render_to_react:(node:SleepyNode, returns:str),
#       render_to_json:(node:SleepyNode, returns:Dict),
#       _resolve_api_binding:(path:str, returns:str),
#       _get_css_classes:(node:SleepyNode, returns:str)
#     )
#   ),
#   
#   main_flow:(
#     demo:(
#       syntax_examples:[
#         "{card:(column:[h1:api.user.name, p:api.user.email])}",
#         "{dashboard$dark:(row:[sidebar, main:(column:[header, content])])}"
#       ],
#       workflow:(
#         step1:(action:tokenize, input:syntax_examples),
#         step2:(action:parse, input:tokens),
#         step3:(action:render, output:[html, react, json])
#       )
#     )
#   )
# )}

import re
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

class TokenType(Enum):
    OPEN_BRACE = "OPEN_BRACE"
    CLOSE_BRACE = "CLOSE_BRACE" 
    OPEN_PAREN = "OPEN_PAREN"
    CLOSE_PAREN = "CLOSE_PAREN"
    OPEN_BRACKET = "OPEN_BRACKET"
    CLOSE_BRACKET = "CLOSE_BRACKET"
    COLON = "COLON"
    COMMA = "COMMA"
    IDENTIFIER = "IDENTIFIER"
    API_BINDING = "API_BINDING"
    STYLE_VARIANT = "STYLE_VARIANT"
    EOF = "EOF"

@dataclass
class Token:
    type: TokenType
    value: str
    position: int

@dataclass
class SleepyNode:
    node_type: str
    name: Optional[str] = None
    children: List['SleepyNode'] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    api_binding: Optional[str] = None
    style_variant: Optional[str] = None

class SleepyLexer:
    # {lexer_implementation:(
    #   initialization:(
    #     store:input_text,
    #     set:position_to_zero,
    #     prepare:token_patterns
    #   ),
    #   tokenization_logic:(
    #     while:not_at_end:(
    #       skip:whitespace,
    #       match:bracket_patterns,
    #       detect:api_bindings,
    #       identify:style_variants,
    #       collect:identifiers
    #     )
    #   )
    # )}
    
    def __init__(self, text: str):
        self.text = text
        self.position = 0
        self.tokens: List[Token] = []
    
    def tokenize(self) -> List[Token]:
        while self.position < len(self.text):
            self._skip_whitespace()
            
            if self.position >= len(self.text):
                break
                
            char = self._current_char()
            
            if char == '{':
                self.tokens.append(Token(TokenType.OPEN_BRACE, char, self.position))
                self._advance()
            elif char == '}':
                self.tokens.append(Token(TokenType.CLOSE_BRACE, char, self.position))
                self._advance()
            elif char == '(':
                self.tokens.append(Token(TokenType.OPEN_PAREN, char, self.position))
                self._advance()
            elif char == ')':
                self.tokens.append(Token(TokenType.CLOSE_PAREN, char, self.position))
                self._advance()
            elif char == '[':
                self.tokens.append(Token(TokenType.OPEN_BRACKET, char, self.position))
                self._advance()
            elif char == ']':
                self.tokens.append(Token(TokenType.CLOSE_BRACKET, char, self.position))
                self._advance()
            elif char == ':':
                self.tokens.append(Token(TokenType.COLON, char, self.position))
                self._advance()
            elif char == ',':
                self.tokens.append(Token(TokenType.COMMA, char, self.position))
                self._advance()
            elif char.isalpha() or char == '_':
                identifier = self._read_identifier()
                
                # Check for API binding
                if identifier == 'api' and self._peek_char() == '.':
                    api_binding = self._read_api_binding()
                    self.tokens.append(Token(TokenType.API_BINDING, api_binding, self.position - len(api_binding)))
                # Check for style variant
                elif '$' in identifier:
                    parts = identifier.split('$', 1)
                    base = parts[0]
                    variant = parts[1] if len(parts) > 1 else ''
                    self.tokens.append(Token(TokenType.STYLE_VARIANT, identifier, self.position - len(identifier)))
                else:
                    self.tokens.append(Token(TokenType.IDENTIFIER, identifier, self.position - len(identifier)))
            else:
                self._advance()  # Skip unknown characters
        
        self.tokens.append(Token(TokenType.EOF, '', self.position))
        return self.tokens
    
    def _current_char(self) -> Optional[str]:
        if self.position >= len(self.text):
            return None
        return self.text[self.position]
    
    def _peek_char(self) -> Optional[str]:
        peek_pos = self.position + 1
        if peek_pos >= len(self.text):
            return None
        return self.text[peek_pos]
    
    def _advance(self):
        self.position += 1
    
    def _skip_whitespace(self):
        while self.position < len(self.text) and self.text[self.position].isspace():
            self.position += 1
    
    def _read_identifier(self) -> str:
        start = self.position
        while (self.position < len(self.text) and 
               (self.text[self.position].isalnum() or self.text[self.position] in '_$')):
            self.position += 1
        return self.text[start:self.position]
    
    def _read_api_binding(self) -> str:
        start = self.position
        while (self.position < len(self.text) and 
               (self.text[self.position].isalnum() or self.text[self.position] in '._')):
            self.position += 1
        return self.text[start:self.position]

class SleepyParser:
    # {parser_implementation:(
    #   initialization:(
    #     store:token_list,
    #     set:current_position_zero
    #   ),
    #   parsing_logic:(
    #     parse_root_component:(
    #       expect:open_brace,
    #       read:component_name,
    #       parse:children_or_content,
    #       expect:close_brace
    #     ),
    #     parse_children:(
    #       while:not_closing_bracket:(
    #         parse:nested_component,
    #         handle:comma_separation
    #       )
    #     )
    #   )
    # )}
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
    
    def parse(self) -> SleepyNode:
        return self._parse_component()
    
    def _current_token(self) -> Optional[Token]:
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position]
    
    def _advance(self):
        self.position += 1
    
    def _parse_component(self) -> SleepyNode:
        # Expect {
        if self._current_token().type != TokenType.OPEN_BRACE:
            raise ValueError(f"Expected {{, got {self._current_token().value}")
        self._advance()
        
        # Get component name
        token = self._current_token()
        if token.type in [TokenType.IDENTIFIER, TokenType.STYLE_VARIANT]:
            name = token.value
            style_variant = None
            
            # Handle style variants
            if '$' in name:
                parts = name.split('$', 1)
                name = parts[0]
                style_variant = parts[1]
            
            self._advance()
        else:
            raise ValueError(f"Expected component name, got {token.value}")
        
        # Expect :
        if self._current_token().type != TokenType.COLON:
            raise ValueError(f"Expected :, got {self._current_token().value}")
        self._advance()
        
        # Create node
        node = SleepyNode(
            node_type="component",
            name=name,
            style_variant=style_variant
        )
        
        # Parse content
        current = self._current_token()
        if current.type == TokenType.OPEN_PAREN:
            # Layout with children
            self._advance()  # Skip (
            node.children = self._parse_children()
            if self._current_token().type != TokenType.CLOSE_PAREN:
                raise ValueError(f"Expected ), got {self._current_token().value}")
            self._advance()
        elif current.type == TokenType.API_BINDING:
            # API binding
            node.api_binding = current.value
            self._advance()
        elif current.type == TokenType.IDENTIFIER:
            # Static content
            node.attributes['content'] = current.value
            self._advance()
        
        # Expect }
        if self._current_token().type != TokenType.CLOSE_BRACE:
            raise ValueError(f"Expected }}, got {self._current_token().value}")
        self._advance()
        
        return node
    
    def _parse_children(self) -> List[SleepyNode]:
        children = []
        
        while (self._current_token() and 
               self._current_token().type not in [TokenType.CLOSE_PAREN, TokenType.EOF]):
            
            current = self._current_token()
            
            if current.type == TokenType.OPEN_BRACKET:
                # Array of elements
                self._advance()  # Skip [
                while (self._current_token() and 
                       self._current_token().type != TokenType.CLOSE_BRACKET):
                    children.append(self._parse_element())
                    if self._current_token().type == TokenType.COMMA:
                        self._advance()
                if self._current_token().type == TokenType.CLOSE_BRACKET:
                    self._advance()
            else:
                children.append(self._parse_element())
                if self._current_token().type == TokenType.COMMA:
                    self._advance()
        
        return children
    
    def _parse_element(self) -> SleepyNode:
        current = self._current_token()
        
        if current.type == TokenType.OPEN_BRACE:
            # Nested component
            return self._parse_component()
        elif current.type in [TokenType.IDENTIFIER, TokenType.STYLE_VARIANT]:
            # Simple element
            name = current.value
            style_variant = None
            
            if '$' in name:
                parts = name.split('$', 1)
                name = parts[0]
                style_variant = parts[1]
            
            self._advance()
            
            node = SleepyNode(
                node_type="element", 
                name=name,
                style_variant=style_variant
            )
            
            if (self._current_token() and 
                self._current_token().type == TokenType.COLON):
                self._advance()
                next_token = self._current_token()
                
                if next_token.type == TokenType.API_BINDING:
                    node.api_binding = next_token.value
                    self._advance()
                elif next_token.type == TokenType.IDENTIFIER:
                    node.attributes['content'] = next_token.value
                    self._advance()
                elif next_token.type == TokenType.OPEN_PAREN:
                    self._advance()
                    node.children = self._parse_children()
                    if self._current_token().type == TokenType.CLOSE_PAREN:
                        self._advance()
            
            return node
        elif current.type == TokenType.API_BINDING:
            # Direct API binding
            node = SleepyNode(node_type="api_binding", api_binding=current.value)
            self._advance()
            return node
        else:
            raise ValueError(f"Unexpected token: {current.value}")

class SleepyRenderer:
    # {renderer_implementation:(
    #   initialization:(
    #     store:api_data_context,
    #     prepare:style_mappings
    #   ),
    #   rendering_methods:(
    #     html_output:(
    #       traverse:node_tree,
    #       apply:css_classes,
    #       resolve:api_bindings,
    #       generate:html_tags
    #     ),
    #     react_output:(
    #       generate:jsx_components,
    #       apply:tailwind_classes,
    #       handle:event_bindings
    #     )
    #   )
    # )}
    
    def __init__(self, api_data: Dict = None):
        self.api_data = api_data or {}
    
    def render_to_html(self, node: SleepyNode) -> str:
        if node.node_type == "component":
            css_classes = self._get_css_classes(node)
            children_html = ''.join(self.render_to_html(child) for child in node.children)
            return f'<div class="{css_classes}">{children_html}</div>'
        
        elif node.node_type == "element":
            content = ""
            if node.api_binding:
                content = self._resolve_api_binding(node.api_binding)
            elif 'content' in node.attributes:
                content = node.attributes['content']
            
            tag_map = {
                'h1': 'h1', 'h2': 'h2', 'h3': 'h3',
                'p': 'p', 'span': 'span',
                'button': 'button', 'input': 'input',
                'img': 'img'
            }
            
            tag = tag_map.get(node.name, 'div')
            css_classes = self._get_css_classes(node)
            
            if tag == 'img' and node.api_binding:
                return f'<img src="{content}" class="{css_classes}" alt="Image" />'
            elif tag == 'input':
                return f'<input placeholder="{content}" class="{css_classes}" />'
            else:
                return f'<{tag} class="{css_classes}">{content}</{tag}>'
        
        return ""
    
    def render_to_react(self, node: SleepyNode) -> str:
        if node.node_type == "component":
            css_classes = self._get_css_classes(node)
            children_jsx = '\n'.join(self.render_to_react(child) for child in node.children)
            return f'<div className="{css_classes}">\n{children_jsx}\n</div>'
        
        elif node.node_type == "element":
            content = ""
            if node.api_binding:
                content = f"{{{node.api_binding.replace('api.', 'data.')}}}"
            elif 'content' in node.attributes:
                content = node.attributes['content'].replace('_', ' ')
            
            css_classes = self._get_css_classes(node)
            
            if node.name == 'img' and node.api_binding:
                return f'<img src={content} className="{css_classes}" alt="Image" />'
            elif node.name == 'input':
                return f'<input placeholder="{content}" className="{css_classes}" />'
            elif node.name in ['h1', 'h2', 'h3', 'p', 'span', 'button']:
                return f'<{node.name} className="{css_classes}">{content}</{node.name}>'
            else:
                return f'<div className="{css_classes}">{content}</div>'
        
        return ""
    
    def render_to_json(self, node: SleepyNode) -> Dict:
        return {
            'type': node.node_type,
            'name': node.name,
            'api_binding': node.api_binding,
            'style_variant': node.style_variant,
            'attributes': node.attributes,
            'children': [self.render_to_json(child) for child in node.children]
        }
    
    def _resolve_api_binding(self, path: str) -> str:
        if not path.startswith('api.'):
            return path
        
        keys = path[4:].split('.')  # Remove 'api.' prefix
        current = self.api_data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return f"[{path}]"
        
        return str(current)
    
    def _get_css_classes(self, node: SleepyNode) -> str:
        base_classes = {
            'card': 'bg-white rounded-lg shadow-md p-4',
            'column': 'flex flex-col',
            'row': 'flex flex-row items-center',
            'button': 'px-4 py-2 rounded-lg',
            'input': 'px-3 py-2 border rounded-md'
        }
        
        classes = base_classes.get(node.name, '')
        
        if node.style_variant:
            variant_classes = {
                'primary': 'bg-blue-500 text-white hover:bg-blue-600',
                'secondary': 'bg-gray-500 text-white hover:bg-gray-600',
                'ghost': 'bg-transparent hover:bg-gray-100'
            }
            classes += ' ' + variant_classes.get(node.style_variant, '')
        
        return classes.strip()

def main():
    # {main_execution:(
    #   demo_data:(
    #     api_mock:(
    #       user:(name:"John Doe", email:"john@example.com"),
    #       posts:[
    #         (title:"First Post", content:"Hello World"),
    #         (title:"Second Post", content:"SleepySyntax rocks!")
    #       ]
    #     )
    #   ),
    #   test_cases:[
    #     simple_card,
    #     complex_dashboard,
    #     api_binding_example
    #   ],
    #   workflow:(
    #     for_each:test_case:(
    #       step1:tokenize_syntax,
    #       step2:parse_tokens,
    #       step3:render_outputs,
    #       step4:display_results
    #     )
    #   )
    # )}
    
    print("🌙 SleepySyntax Parser Demo")
    print("Written in SleepySyntax syntax!")
    print("=" * 50)
    
    api_data = {
        'user': {
            'name': 'John Doe',
            'email': 'john@example.com'
        },
        'posts': [
            {'title': 'First Post', 'content': 'Hello World!'},
            {'title': 'Second Post', 'content': 'SleepySyntax is amazing!'}
        ]
    }
    
    test_cases = [
        "{card:(column:[h1:api.user.name, p:api.user.email])}",
        "{dashboard$dark:(row:[sidebar, main:(column:[header, content])])}",
        "{button$primary:Click_Me}"
    ]
    
    for i, syntax in enumerate(test_cases, 1):
        print(f"\n🔍 Test Case {i}:")
        print(f"Syntax: {syntax}")
        
        try:
            # Tokenize
            lexer = SleepyLexer(syntax)
            tokens = lexer.tokenize()
            print(f"Tokens: {[f'{t.type.value}:{t.value}' for t in tokens if t.type != TokenType.EOF]}")
            
            # Parse
            parser = SleepyParser(tokens)
            ast = parser.parse()
            
            # Render
            renderer = SleepyRenderer(api_data)
            html = renderer.render_to_html(ast)
            react = renderer.render_to_react(ast)
            json_output = renderer.render_to_json(ast)
            
            print(f"HTML: {html}")
            print(f"React: {react}")
            print(f"JSON: {json.dumps(json_output, indent=2)}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n✨ Meta-programming complete!")
    print("A SleepySyntax parser written in SleepySyntax! 🌙")

if __name__ == "__main__":
    main()