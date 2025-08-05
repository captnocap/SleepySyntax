# SleepySyntax Primitives Library

*The syntax format that finally let you sleep at night*

## Core Containers

### Layout Containers
```
{div:(column:[...])}           // Basic vertical container
{div:(row:[...])}              // Basic horizontal container
{section:(column:[...])}       // Semantic section container
{article:(column:[...])}       // Article/content container
{aside:(row:[...])}            // Sidebar container
{header:(row:[...])}           // Header container
{footer:(row:[...])}           // Footer container
{main:(column:[...])}          // Main content area
```

### Visual Containers
```
{card:(column:[...])}          // Card with shadow/border
{panel:(column:[...])}         // Simple panel container
{box:(row:[...])}              // Basic box container
{container:(column:[...])}     // Max-width centered container
{wrapper:(column:[...])}       // Full-width wrapper
{modal:(column:[...])}         // Modal/dialog container
{popover:(column:[...])}       // Popover container
```

## Text Elements

### Headings
```
h1:api.title                   // Large heading
h2:api.subtitle                // Medium heading  
h3:api.section                 // Small heading
h4:api.subsection              // Extra small heading
h5:api.label                   // Tiny heading
h6:api.caption                 // Micro heading
```

### Text Content
```
p:api.content                  // Paragraph text
span:api.label                 // Inline text
text:api.value                 // Generic text
label:api.fieldName            // Form label
caption:api.description        // Small caption text
code:api.snippet               // Inline code
pre:api.codeBlock              // Code block
blockquote:api.quote           // Quote block
```

### Text Styling
```
strong:api.important           // Bold text
em:api.emphasis                // Italic text
mark:api.highlight             // Highlighted text
small:api.fine                 // Small text
sub:api.subscript              // Subscript
sup:api.superscript            // Superscript
del:api.removed                // Strikethrough text
```

## Interactive Elements

### Buttons
```
button:api.text                // Primary button
button_secondary:api.text      // Secondary button  
button_ghost:api.text          // Ghost/minimal button
button_danger:api.text         // Destructive button
button_success:api.text        // Success button
button_outline:api.text        // Outlined button
button_link:api.text           // Link-style button
icon_button:icon_name          // Icon-only button
```

### Links
```
link:api.url                   // Basic link
link_external:api.url          // External link with icon
link_button:api.url            // Button-styled link
nav_link:api.url               // Navigation link
breadcrumb_link:api.url        // Breadcrumb link
```

### Form Elements
```
input:api.value                // Text input
input_email:api.email          // Email input
input_password:api.password    // Password input
input_number:api.number        // Number input
input_search:api.query         // Search input
textarea:api.content           // Multi-line text
select:api.options             // Dropdown select
checkbox:api.checked           // Checkbox
radio:api.selected             // Radio button
toggle:api.enabled             // Toggle switch
slider:api.value               // Range slider
```

## Media Elements

### Images
```
img:api.src                    // Basic image
img_avatar:api.user.avatar     // Avatar image (circular)
img_cover:api.cover            // Cover/hero image
img_thumbnail:api.thumb        // Small thumbnail
img_icon:api.icon              // Icon-sized image
img_logo:api.brand.logo        // Logo image
```

### Media
```
video:api.src                  // Video element
audio:api.src                  // Audio element
iframe:api.embed               // Embedded iframe
canvas:api.data                // Canvas element
svg:api.path                   // SVG element
```

## Data Display

### Lists
```
ul:(li:[api.items])            // Unordered list
ol:(li:[api.items])            // Ordered list
dl:(dt_dd:[api.terms])         // Definition list
nav_list:(li:[api.links])      // Navigation list
menu:(li:[api.items])          // Menu list
```

### Tables
```
table:(thead:[tr:(th:[api.headers])], tbody:[tr:(td:[api.rows])])
simple_table:api.data          // Simple data table
data_table:api.complex         // Complex data table with sorting
```

### Data Structures
```
grid:api.items                 // CSS Grid layout
masonry:api.items              // Masonry/Pinterest layout
carousel:api.slides            // Image carousel
tabs:(tab:[api.tabs])          // Tab container
accordion:(panel:[api.items])  // Accordion container
```

## Layout Utilities

### Spacing
```
spacer:sm                      // Small spacer
spacer:md                      // Medium spacer  
spacer:lg                      // Large spacer
divider:horizontal             // Horizontal divider line
divider:vertical               // Vertical divider line
```

### Positioning
```
sticky:(column:[...])          // Sticky positioned
fixed:(row:[...])              // Fixed positioned
absolute:(div:[...])           // Absolute positioned
relative:(column:[...])        // Relative positioned
```

## Data Iteration

### Loops
```
forEach:api.items:[template]                    // Basic iteration
forEach:api.users:[card:(row:[...])]          // Card list iteration
forEach:api.posts:[article:(column:[...])]    // Article iteration
map:api.data:[component]                       // Map operation
filter:api.items.active:[template]            // Filtered iteration
```

### Conditional Rendering
```
if:api.user.isLoggedIn:[template]             // Conditional display
unless:api.loading:[content]                  // Negative conditional
show:api.hasData:[template]                   // Show if truthy
hide:api.error:[template]                     // Hide if truthy
```

## State & Loading

### Loading States
```
loading:(spinner:md)                          // Loading spinner
skeleton:(column:[bar, bar, bar])             // Skeleton loader
placeholder:api.message                       // Placeholder text
empty_state:(column:[icon, text])             // Empty state
```

### Error States
```
error:(column:[icon:error, p:api.message])    // Error display
warning:(row:[icon:warning, span:api.text])   // Warning message
success:(row:[icon:check, span:api.text])     // Success message
info:(row:[icon:info, span:api.text])         // Info message
```

## Complex Components

### Navigation
```
navbar:(row:[logo, nav:(row:[link, link, link]), actions:(row:[button, avatar])])
sidebar:(column:[nav:(column:[link, link, link]), footer])
breadcrumbs:(row:[link, separator, link, separator, text])
pagination:(row:[button:prev, pages:(row:[button, button, button]), button:next])
```

### Layouts
```
hero:(column:[h1, p, button])
feature:(row:[img, column:[h2, p, link]])
cta:(column:[h2, p, row:[button, button]])
testimonial:(column:[blockquote, row:[avatar, column:[name, title]]])
pricing:(column:[h3, price, ul, button])
```

### Complex Cards
```
product_card:(column:[img, column:[h3, p, row:[price, button]]])
user_card:(row:[avatar, column:[h3, p, row:[button, button]]])  
blog_card:(column:[img, column:[date, h3, p, link]])
stat_card:(column:[row:[h2, icon], p, change])
```

## API Data Patterns

### User Data
```
user_profile:(column:[
  img_avatar:api.user.avatar,
  h1:api.user.name,
  p:api.user.email,
  p:api.user.role
])
```

### Product Data  
```
product_grid:forEach:api.products:[
  card:(column:[
    img:item.image,
    h3:item.name,
    p:item.price,
    button:Add_to_Cart
  ])
]
```

### Dashboard Data
```
dashboard:(column:[
  row:[
    stat_card:(column:[h2:api.stats.users, p:Total_Users]),
    stat_card:(column:[h2:api.stats.revenue, p:Revenue]),
    stat_card:(column:[h2:api.stats.orders, p:Orders])
  ],
  row:[
    card:(column:[h3:Recent_Activity, forEach:api.activity:[...]]),
    card:(column:[h3:Top_Products, forEach:api.products:[...]])
  ]
])
```

## Responsive Patterns

### Breakpoint Containers
```
mobile:(column:[...])          // Mobile-only content
tablet:(row:[...])             // Tablet-only content  
desktop:(grid:[...])           // Desktop-only content
responsive:(mobile:column, desktop:row)  // Responsive layout
```

### Adaptive Components
```
adaptive_nav:(mobile:hamburger, desktop:full_nav)
adaptive_card:(mobile:column, desktop:row)
adaptive_grid:(mobile:1_col, tablet:2_col, desktop:3_col)
```

---

## Usage Examples

### Simple Page Layout
```
{main:(column:[
  header:(row:[logo, nav:(row:[link, link, link])]),
  section:(column:[h1:api.title, p:api.content]),
  footer:(row:[p:copyright, nav:(row:[link, link])])
])}
```

### E-commerce Product Page
```
{main:(column:[
  section:(row:[
    img_cover:api.product.image,
    column:[
      h1:api.product.name,
      p:api.product.price,
      p:api.product.description,
      row:[button:Add_to_Cart, button_secondary:Add_to_Wishlist]
    ]
  ]),
  section:(column:[
    h2:Related_Products,
    forEach:api.related:[
      card:(column:[img:item.image, h3:item.name, p:item.price])
    ]
  ])
])}
```

### Dashboard Layout
```
{div:(row:[
  sidebar:(column:[
    nav:(column:[link:Dashboard, link:Users, link:Orders])
  ]),
  main:(column:[
    header:(row:[h1:Dashboard, button:New_Item]),
    row:[
      stat_card:(column:[h2:api.stats.users, p:Users]),
      stat_card:(column:[h2:api.stats.orders, p:Orders])
    ],
    card:(column:[
      h3:Recent_Activity,
      forEach:api.activity:[
        row:[img_avatar:item.user.avatar, column:[p:item.action, small:item.time]]
      ]
    ])
  ])
])}
```

---

*SleepySyntax: Because building UI shouldn't keep you up at night* 🌙