# SleepySyntax Rainbow Coloring Analysis

## Overview
Based on analysis of `bank.sleepy` and `medical.sleepy`, here's the complete syntax structure for implementing rainbow CSV-style coloring.

## Core Syntax Patterns

### 1. **Nesting Structure (Rainbow Levels)**
```
Level 1: {root$theme:(...)  }           # 🔴 RED
Level 2:   section:(...)                # 🔵 BLUE  
Level 3:     element:[...]              # 🟢 GREEN
Level 4:       subelement:(...)         # 🟣 MAGENTA
Level 5:         nested:[...]           # 🟠 ORANGE
Level 6:           deep:(...)           # 🟡 YELLOW
```

### 2. **Key Patterns by Context**

#### **Root Level (Level 1 - RED)**
```
{enterprise_bank$secure_theme:(           # Key + Style + Container
{medivault$secure_healthcare:(            # Key + Style + Container
```

#### **Section Level (Level 2 - BLUE)**
```
styles:(                                  # Section keyword
frontend:(                               # Section keyword  
api:(                                    # Section keyword
database:(                              # Section keyword
```

#### **Container Level (Level 3 - GREEN)**
```
base:[...]                              # Array container
auth:(...)                              # Parentheses container
login:(...)                             # Nested container
```

#### **Element Level (Level 4 - MAGENTA)**
```
button$primary:(...)                     # Element + Style
input_email$auth:(...)                  # Element + Type + Style
card$auth:(...)                         # Element + Style
```

#### **Content Level (Level 5 - ORANGE)**
```
row:[...]                               # Layout elements
column:[...]                            # Layout elements
span$bold:(...)                         # Text elements
```

#### **Deep Level (Level 6 - YELLOW)**
```
icon: dashboard                          # Simple key-value
span: Google                            # Simple key-value
h1: Welcome_Back                        # Simple key-value
```

## 3. **Special Token Types (Light Colors)**

### **Style Identifiers - Light Yellow**
```
$secure_theme                           # Theme styles
$primary                                # Button styles
$auth                                   # Context styles
$danger                                 # State styles
$ghost                                  # Appearance styles
```

### **API Calls - Light Blue**  
```
api.auth.email                          # API data binding
api.user.name                           # API data binding
item.name                               # Iterator binding
api.stats.activePatients               # API statistics
```

### **Control Flow - Light Green**
```
forEach: api.patients.recent:[...]      # Loop control
if: user.exists:(...)                   # Conditional
unless: api.balance.isVisible:[...]     # Negative conditional
else:(...)                              # Alternative
```

## 4. **Complex Pattern Examples**

### **Multi-Style Elements**
```
input_email$auth: api.auth.email
│     │      │    │
│     │      │    └── API Call (Light Blue)
│     │      └────── Style (Light Yellow)  
│     └─────────── Element Type
└───────────────── Element Name (Color by nesting level)
```

### **Nested Control Flow**
```
forEach: api.bills.upcoming: [
│        │                   │
│        │                   └── Container (Next level color)
│        └─────────────────── API Call (Light Blue)
└──────────────────────────── Control Flow (Light Green)
```

### **Inline Styles with Values**
```
input$wide,placeholder:(Type here...):api.function.input
│          │             │              │
│          │             │              └── API Call (Light Blue)
│          │             └────────────── Value content
│          └──────────────────────────── Inline Style (Light Yellow)
└─────────────────────────────────────── Element (Color by level)
```

## 5. **Database & API Specific Patterns**

### **HTTP Methods & Paths**
```
POST:/auth/login:(...)                  # Method + Path
GET:/patients/:id:(...)                 # Method + Path with param
```

### **Database Schema**
```
users:(                                 # Table name
  id: uuid_primary,                     # Field + Type + Constraint
  email: string_unique_required,        # Field + Type + Constraints
  createdAt: timestamp_auto             # Field + Type + Auto
)
```

### **API Response Patterns**
```
returns:(                               # API response
  token: token,                         # Return field
  user: user.safe_profile,              # Return field with data
  accounts: db.accounts.findByUserId(   # Return field with DB call
    user.id
  )
)
```

## 6. **Color Mapping Strategy**

### **Rainbow Progression (Bold/Saturated)**
1. **Level 1 - Red (#ff6b6b)**: Root containers, themes
2. **Level 2 - Blue (#4ecdc4)**: Major sections  
3. **Level 3 - Green (#50fa7b)**: Containers, arrays
4. **Level 4 - Magenta (#ff79c6)**: UI elements with styles
5. **Level 5 - Orange (#ffb86c)**: Layout elements  
6. **Level 6 - Yellow (#f1fa8c)**: Content, values

### **Special Tokens (Light Variants)**
- **Light Yellow (#fff3a0)**: `$` style identifiers
- **Light Blue (#b8e6ff)**: `api.`, `item.`, `db.` calls
- **Light Green (#a7f3d0)**: `forEach`, `if`, `unless`, `else`

## 7. **Implementation Rules**

### **Priority Order** (when tokens overlap)
1. Control flow keywords (`forEach`, `if`) = Light Green
2. API/Data calls (`api.`, `item.`, `db.`) = Light Blue  
3. Style identifiers (`$anything`) = Light Yellow
4. Element names = Rainbow color by nesting depth
5. Values and content = Default or rainbow by depth

### **Regex Patterns Needed**
```javascript
// Control flow
/\b(forEach|if|unless|else)\b/

// API calls  
/\b(api|item|db)\.[a-zA-Z0-9_.]+\b/

// Style identifiers
/\$[a-zA-Z_][a-zA-Z0-9_-]*/

// HTTP methods
/\b(GET|POST|PUT|DELETE|PATCH)\b/

// Element with style + API
/([a-zA-Z_][a-zA-Z0-9_]*)(\$[a-zA-Z_][a-zA-Z0-9_-]*)?(:)(\s*(api|item|db)\.[a-zA-Z0-9_.]+)?/
```

## 8. **Visual Goals**

The rainbow coloring should make it **immediately obvious**:
- Which elements belong to the same nesting level
- What type of token each element is (API, style, control flow)
- The hierarchical structure of complex nested expressions
- Matching opening/closing brackets and parentheses

This creates a **visual parsing system** where developers can instantly understand the structure and relationships in complex sleepy syntax files.