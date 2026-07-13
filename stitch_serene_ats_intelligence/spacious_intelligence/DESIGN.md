---
name: Spacious Intelligence
colors:
  surface: '#fff8f5'
  surface-dim: '#e2d8d3'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fdf1ed'
  surface-container: '#f7ece7'
  surface-container-high: '#f1e6e1'
  surface-container-highest: '#ebe0dc'
  on-surface: '#1f1b18'
  on-surface-variant: '#414751'
  inverse-surface: '#352f2c'
  inverse-on-surface: '#faeeea'
  outline: '#717783'
  outline-variant: '#c1c7d3'
  surface-tint: '#0060ac'
  primary: '#005da7'
  on-primary: '#ffffff'
  primary-container: '#2976c7'
  on-primary-container: '#fdfcff'
  inverse-primary: '#a4c9ff'
  secondary: '#4f5e7e'
  on-secondary: '#ffffff'
  secondary-container: '#cadaff'
  on-secondary-container: '#505f7f'
  tertiary: '#5c5c59'
  on-tertiary: '#ffffff'
  tertiary-container: '#757572'
  on-tertiary-container: '#fefcf8'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d4e3ff'
  primary-fixed-dim: '#a4c9ff'
  on-primary-fixed: '#001c39'
  on-primary-fixed-variant: '#004883'
  secondary-fixed: '#d7e2ff'
  secondary-fixed-dim: '#b7c7eb'
  on-secondary-fixed: '#091b37'
  on-secondary-fixed-variant: '#374765'
  tertiary-fixed: '#e4e2de'
  tertiary-fixed-dim: '#c8c6c3'
  on-tertiary-fixed: '#1b1c1a'
  on-tertiary-fixed-variant: '#474744'
  background: '#fff8f5'
  on-background: '#1f1b18'
  surface-variant: '#ebe0dc'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-md:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Work Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Work Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-sm:
    fontFamily: Work Sans
    fontSize: 13px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  section-gap: 64px
  card-padding: 40px
  gutter: 24px
  margin-mobile: 20px
  container-max: 1100px
---

## Brand & Style
The design system focuses on reducing the cognitive load and "resume anxiety" inherent in the recruitment process. It prioritizes a calm, academic, yet modern atmosphere that treats information with the dignity of a physical document while providing the efficiency of an intelligent tool.

The aesthetic is a blend of **Minimalism** and **Tactile** design. It utilizes a "Paper-on-Cream" layering strategy where white surfaces float over a warm, organic background. The emotional response is one of clarity, breathability, and professional composure. Large amounts of white space are intentional, ensuring that the ATS analysis results never feel overwhelming or cluttered.

## Colors
The palette is rooted in a warm, low-fatigue cream (`#FDFBF7`) which serves as the global canvas. 

- **Primary Blue:** Used exclusively for high-intent actions, progress indicators, and active states. It provides a professional anchor to the soft background.
- **Deep Navy:** Reserved for headlines to ensure strong information hierarchy and readability.
- **Charcoal Brown:** Used for body text to maintain high contrast while feeling softer and more organic than pure black.
- **Semantic Accents:** These utilize a "washed out" background with high-saturation text to denote ATS scoring categories (e.g., Match, Warning, Missing, Neutral) without breaking the airy aesthetic.

## Typography
The typography system uses **Manrope** for structural elements to provide a modern, balanced feel. **Work Sans** is used for all functional and body text due to its exceptional legibility and grounded nature, which is critical when reviewing dense resume data.

Line heights are intentionally set wider than standard (1.6 for body) to facilitate a comfortable reading pace. Display and headline weights are kept bold to provide clear anchors in a layout that uses minimal borders.

## Layout & Spacing
This design system employs a **Fixed Grid** philosophy for desktop to prevent line lengths from becoming unreadable. The "One Idea Per Card" rule dictates the layout: sections are separated by massive vertical gaps (`64px`) to ensure the user focuses on one metric or insight at a time.

- **Desktop:** 12-column grid within a 1100px container.
- **Tablet:** 8-column grid with 32px margins.
- **Mobile:** 4-column fluid grid with 20px margins; card padding reduces to 24px to preserve screen real estate while maintaining the "airy" feel.

## Elevation & Depth
Depth is achieved through **Ambient Shadows** and tonal layering. There are no hard borders in the system.

1.  **Canvas (Level 0):** The Cream (`#FDFBF7`) background.
2.  **Surface (Level 1):** Pure White (`#FFFFFF`) cards. These use a very wide, soft shadow: `0px 12px 32px rgba(27, 43, 72, 0.04)`. The shadow is slightly tinted with the Deep Navy headline color to keep it grounded.
3.  **Active/Hover (Level 2):** When a card or element is focused, the shadow deepens and expands slightly: `0px 20px 48px rgba(27, 43, 72, 0.08)`.

This creates a "floating paper" effect that feels tactile and premium.

## Shapes
The shape language is consistently soft but structured. 

- **Cards/Modules:** Use `rounded-xl` (1.5rem / 24px) to emphasize the friendly, modern aesthetic.
- **Buttons & Inputs:** Use `rounded-lg` (1rem / 16px) for a comfortable, clickable appearance.
- **Status Chips:** Use fully rounded (pill) shapes to distinguish them from interactive buttons.

## Components

- **Buttons:** Primary buttons use the Calm Mid-Blue background with white text. No borders. They should have a subtle scale-up (1.02x) on hover rather than a dramatic color shift.
- **Cards:** The primary container. Every card must have a minimum of 40px padding on all sides. Content within cards should be vertically stacked with 24px gaps.
- **ATS Chips:** Small pill-shaped badges using the semantic colors. They appear in the top right of cards to provide immediate status (e.g., "High Match").
- **Input Fields:** Pure white backgrounds on the cream canvas. Borders are replaced by a soft 1px stroke in a very light grey-blue, which thickens and turns Primary Blue on focus.
- **Progress Rings:** Used for "Match Percentage." Utilize a thick 8px stroke with the Primary Blue, featuring rounded caps on the stroke-end.
- **Lists:** Resume bullet points should have increased vertical spacing (12px between items) and use the Primary Blue for the bullet character to guide the eye.