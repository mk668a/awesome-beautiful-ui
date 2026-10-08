# Awesome Beautiful UI

> Open source UI that is beautiful and still being maintained.

You find a gorgeous shader background or text effect, wire it into your app, and only later notice that the last commit was two years ago. Visual libraries are especially prone to this. Once the effect looks finished, the author moves on, and the next framework release breaks it.

This list covers the web (components, motion, WebGL), the terminal, and the small widgets in between. It has two rules.

1. **Still maintained.** A project stays in the main list only while it has had a push in the last three months. This is read from the GitHub API every time the list is regenerated, not judged by hand.
2. **Something of its own.** Each entry has an effect, an idea or a level of polish you would recognize. Another collection of copy-paste components with nothing distinctive does not get in.

Projects that fail rule 1 but are too good to forget are kept under [Quiet classics](#quiet-classics).

## How to read an entry

```md
- [Lenis](https://github.com/darkroomengineering/lenis) - Smooth inertial scrolling. `★ 16k` `MIT` `2026-10`
```

The three tags are the star count, the license, and the month of the last push. A ⚠ after the license means it is not a plain permissive license (copyleft, a custom license, or one GitHub could not identify), so read it before you fork or ship.

## Contents

- [Hidden gems](#hidden-gems)
- [Motion and text animation](#motion-and-text-animation)
- [Components and design systems](#components-and-design-systems)
- [WebGL and creative coding](#webgl-and-creative-coding)
- [Terminal and TUI](#terminal-and-tui)
- [Widgets and building blocks](#widgets-and-building-blocks)
- [Quiet classics](#quiet-classics)

<!-- LIST:START -->
_Last refreshed 2026-10-08. 66 active, 20 quiet._

## Hidden gems

Lesser known, each with one effect or idea that is clearly its own.

- [lucide-animated](https://github.com/pqoqubbw/icons) - Lucide-based icons that animate on hover. `★ 8.2k` `MIT` `2026-10`
- [motion-primitives](https://github.com/ibelick/motion-primitives) - Named text and border effects (Text Morph, Scramble, Shimmer Wave, Border Trail) where the motion itself is the product. `★ 6.5k` `MIT` `2026-09`
- [cult-ui](https://github.com/nolly-studio/cult-ui) - Shader-grade components: Warp Shader, Simplex Dithering, Neuro Noise, Fluted Glass, a 3D folded card. `★ 6.4k` `MIT` `2026-10`
- [Chafa](https://github.com/hpjansson/chafa) - Turns images into terminal graphics: character art, Sixel, Kitty and truecolor output. `★ 5.3k` `LGPL-3.0 ⚠` `2026-10`
- [Atropos](https://github.com/nolimits4web/atropos) - Touch-friendly 3D parallax hover cards, from the author of Swiper. `★ 3.6k` `MIT` `2026-10`
- [Paper Shaders](https://github.com/paper-design/shaders) - Zero-dependency canvas shaders: liquid metal, god rays, metaballs, voronoi, CMYK halftone and more. `★ 3.6k` `Apache-2.0` `2026-10`
- [react-colorful](https://github.com/omgovich/react-colorful) - A color picker for React and Preact that weighs about 3 KB. `★ 3.6k` `MIT` `2026-09`
- [ShaderGradient](https://github.com/ruucm/shadergradient) - Animated 3D gradients with film grain, for React, Framer and Figma. `★ 2.8k` `license: see repo ⚠` `2026-09`
- [Kokonut UI](https://github.com/kokonut-labs/kokonutui) - Motion-led components with personality, such as an audio player with EQ and waveform, and glowing orb cards. `★ 2.1k` `MIT` `2026-08`
- [Cally](https://github.com/WickyNilliams/cally) - Small, feature-rich calendar built as framework-agnostic web components. `★ 1.7k` `MIT` `2026-07`
- [slot-text](https://github.com/danielwh2/slot-text) - Slot-machine text roll with zero dependencies, for vanilla JS, React and Vue. `★ 1.0k` `MIT` `2026-09`
- [ditherer](https://github.com/gyng/ditherer) - Browser dithering lab with retro CRT and VHS filters, glitch art and audio-reactive visuals. `★ 95` `MIT` `2026-09`

## Motion and text animation

- [anime.js](https://github.com/juliangarnier/anime) - General-purpose JavaScript animation engine. `★ 73k` `MIT` `2026-08`
- [Motion](https://github.com/motiondivision/motion) - Animation library for React and JavaScript, formerly Framer Motion. `★ 34k` `MIT` `2026-10`
- [react-spring](https://github.com/pmndrs/react-spring) - Spring-physics animation for React. `★ 29k` `MIT` `2026-10`
- [Lenis](https://github.com/darkroomengineering/lenis) - Smooth inertial scrolling. `★ 16k` `MIT` `2026-10`
- [AutoAnimate](https://github.com/formkit/auto-animate) - Zero-config, drop-in transitions when elements are added, removed or moved. `★ 14k` `MIT` `2026-07`

## Components and design systems

- [shadcn/ui](https://github.com/shadcn-ui/ui) - Accessible components you copy into your own codebase and own. `★ 125k` `MIT` `2026-10`
- [React Bits](https://github.com/DavidHDev/react-bits) - Large collection of animated, interactive React components. `★ 49k` `MIT + Commons Clause ⚠` `2026-10`
- [daisyUI](https://github.com/saadeghi/daisyui) - Component class names on top of Tailwind CSS. `★ 43k` `MIT` `2026-09`
- [HeroUI](https://github.com/heroui-inc/heroui) - Modern React UI library, formerly NextUI. `★ 31k` `Apache-2.0` `2026-10`
- [Magic UI](https://github.com/magicuidesign/magicui) - Animated components and effects to copy and paste. `★ 23k` `MIT` `2026-10`
- [HyperUI](https://github.com/markmead/hyperui) - Free Tailwind CSS components. `★ 12k` `MIT` `2026-09`
- [tweakcn](https://github.com/jnsahaj/tweakcn) - Visual theme editor for shadcn/ui. `★ 10k` `Apache-2.0` `2026-09`
- [shadcn-svelte](https://github.com/huntabyte/shadcn-svelte) - shadcn/ui for Svelte. `★ 9.2k` `MIT` `2026-10`
- [Preline UI](https://github.com/htmlstreamofficial/preline) - Prebuilt Tailwind CSS components. `★ 6.5k` `MIT + Preline Fair Use ⚠` `2026-08`
- [Ark UI](https://github.com/chakra-ui/ark) - Unstyled, accessible components for React, Vue, Solid and Svelte. `★ 5.4k` `MIT` `2026-10`

## WebGL and creative coding

- [three.js](https://github.com/mrdoob/three.js) - The JavaScript 3D library. `★ 116k` `MIT` `2026-10`
- [react-three-fiber](https://github.com/pmndrs/react-three-fiber) - React renderer for three.js. `★ 33k` `MIT` `2026-10`
- [p5.js](https://github.com/processing/p5.js) - Creative coding for artists, designers and beginners. `★ 24k` `LGPL-2.1 ⚠` `2026-10`
- [drei](https://github.com/pmndrs/drei) - Ready-made helpers for react-three-fiber. `★ 9.9k` `MIT` `2026-10`
- [tsParticles](https://github.com/tsparticles/tsparticles) - Particles, confetti and fireworks. `★ 9.0k` `MIT` `2026-10`
- [nannou](https://github.com/nannou-org/nannou) - Creative coding framework for Rust. `★ 6.8k` `license: see repo ⚠` `2026-07`
- [gl-react](https://github.com/gre/gl-react) - Write and compose WebGL shaders as React components. `★ 3.0k` `MIT` `2026-10`

## Terminal and TUI

- [lazygit](https://github.com/jesseduffield/lazygit) - Terminal UI for git. `★ 83k` `MIT` `2026-10`
- [bat](https://github.com/sharkdp/bat) - A cat clone with syntax highlighting and git integration. `★ 61k` `Apache-2.0` `2026-10`
- [Starship](https://github.com/starship/starship) - Fast, customizable prompt for any shell. `★ 60k` `ISC` `2026-10`
- [Bubble Tea](https://github.com/charmbracelet/bubbletea) - TUI framework for Go. `★ 45k` `MIT` `2026-10`
- [Ink](https://github.com/vadimdemedes/ink) - React for interactive command-line apps. `★ 40k` `MIT` `2026-10`
- [Textual](https://github.com/Textualize/textual) - Application framework for terminal UIs in Python. `★ 37k` `MIT` `2026-07`
- [btop](https://github.com/aristocratos/btop) - Resource monitor. `★ 35k` `Apache-2.0` `2026-10`
- [k9s](https://github.com/derailed/k9s) - Terminal UI for Kubernetes clusters. `★ 35k` `Apache-2.0` `2026-10`
- [delta](https://github.com/dandavison/delta) - Syntax-highlighting pager for git, diff and grep output. `★ 32k` `MIT` `2026-10`
- [Atuin](https://github.com/atuinsh/atuin) - Searchable, synced shell history. `★ 32k` `MIT` `2026-10`
- [difftastic](https://github.com/Wilfred/difftastic) - Structural diff that understands syntax. `★ 26k` `MIT` `2026-10`
- [fastfetch](https://github.com/fastfetch-cli/fastfetch) - System information tool in the style of neofetch. `★ 25k` `MIT` `2026-10`
- [Gum](https://github.com/charmbracelet/gum) - Styled prompts, spinners and inputs for shell scripts. `★ 24k` `MIT` `2026-09`
- [Oh My Posh](https://github.com/JanDeDobbeleer/oh-my-posh) - Cross-shell prompt renderer. `★ 24k` `MIT` `2026-10`
- [eza](https://github.com/eza-community/eza) - A modern alternative to ls. `★ 24k` `EUPL-1.2 ⚠` `2026-08`
- [Ratatui](https://github.com/ratatui/ratatui) - Rust crate for building terminal UIs. `★ 23k` `MIT` `2026-10`
- [gitui](https://github.com/gitui-org/gitui) - Terminal UI for git, written in Rust. `★ 23k` `MIT` `2026-10`
- [VHS](https://github.com/charmbracelet/vhs) - Records terminal sessions as GIFs from a script. `★ 21k` `MIT` `2026-10`
- [gping](https://github.com/orf/gping) - Ping, but with a graph. `★ 13k` `MIT` `2026-10`
- [onefetch](https://github.com/o2sh/onefetch) - Git repository summary in the terminal. `★ 12k` `MIT` `2026-10`
- [Lip Gloss](https://github.com/charmbracelet/lipgloss) - Style definitions for terminal layouts. `★ 12k` `MIT` `2026-10`
- [Clack](https://github.com/bombshell-dev/clack) - Building blocks for beautiful command-line prompts. `★ 8.1k` `MIT` `2026-10`

## Widgets and building blocks

- [Floating UI](https://github.com/floating-ui/floating-ui) - Positions tooltips, popovers and dropdowns. `★ 33k` `MIT` `2026-09`
- [Recharts](https://github.com/recharts/recharts) - Chart library built with React and D3. `★ 28k` `MIT` `2026-10`
- [Lucide](https://github.com/lucide-icons/lucide) - Consistent, community-made icon set. `★ 25k` `ISC` `2026-10`
- [dnd kit](https://github.com/clauderic/dnd-kit) - Toolkit for drag and drop interfaces. `★ 18k` `MIT` `2026-09`
- [Sonner](https://github.com/emilkowalski/sonner) - The toast component many others are measured against. `★ 13k` `MIT` `2026-08`
- [react-hot-toast](https://github.com/timolins/react-hot-toast) - Lightweight toast notifications for React. `★ 11k` `MIT` `2026-09`
- [wavesurfer.js](https://github.com/katspaugh/wavesurfer.js) - Audio waveform player. `★ 10k` `BSD-3-Clause` `2026-10`
- [React DayPicker](https://github.com/gpbl/react-day-picker) - Date picker and calendar component for React. `★ 6.9k` `MIT` `2026-09`
- [kbar](https://github.com/timc1/kbar) - Command palette for React. `★ 5.3k` `MIT` `2026-08`
- [@hello-pangea/dnd](https://github.com/hello-pangea/dnd) - Accessible drag and drop for lists in React. `★ 4.0k` `Apache-2.0` `2026-10`

## Quiet classics

No push in the last 3 months, or archived. Many of these are simply finished. They move back up on their own when development resumes.

- [Rich](https://github.com/Textualize/rich) - Rich text and beautiful formatting in the terminal, for Python. `★ 57k` `MIT` `2026-06`
- [lazydocker](https://github.com/jesseduffield/lazydocker) - Terminal UI for Docker. `★ 53k` `MIT` `2026-04`
- [lottie-web](https://github.com/airbnb/lottie-web) - Renders After Effects animations on the web. `★ 32k` `MIT` `2025-09`
- [Hover.css](https://github.com/IanLunn/Hover) - A collection of CSS hover effects. `★ 29k` `license: see repo ⚠` `2023-10`
- [GSAP](https://github.com/greensock/GSAP) - The long-standing professional animation platform for the web. `★ 29k` `custom ⚠` `2026-04`
- [AOS](https://github.com/michalsnik/aos) - Animate elements as they scroll into view. `★ 28k` `MIT` `2024-03`
- [visx](https://github.com/airbnb/visx) - Low-level visualization components for React. `★ 21k` `MIT` `2026-06`
- [SpinKit](https://github.com/tobiasahlin/SpinKit) - CSS loading spinners. `★ 19k` `MIT` `2020-08`
- [WebGL Fluid Simulation](https://github.com/PavelDoGreat/WebGL-Fluid-Simulation) - The fluid simulation everyone has played with. `★ 17k` `MIT` `2024-11`
- [typed.js](https://github.com/mattboldt/typed.js) - The typewriter effect. `★ 16k` `license: see repo ⚠` `2026-01`
- [cmdk](https://github.com/dip/cmdk) - The reference command menu component for React. `★ 13k` `MIT` `2025-10`
- [canvas-confetti](https://github.com/catdad/canvas-confetti) - Confetti on a canvas. `★ 13k` `ISC` `2025-10`
- [Theatre.js](https://github.com/theatre-js/theatre) - Motion design editor with a timeline, for the web. `★ 13k` `Apache-2.0` `2024-08`
- [Flowbite](https://github.com/themesberg/flowbite) - Component library built on Tailwind CSS. `★ 9.4k` `MIT` `2026-06`
- [CountUp.js](https://github.com/inorganik/countUp.js) - Animates a number by counting up to it. `★ 8.2k` `MIT` `2026-07`
- [Vanta.js](https://github.com/tengbao/vanta) - Animated 3D backgrounds in a few lines. `★ 7.1k` `MIT` `2024-03`
- [canvas-sketch](https://github.com/mattdesl/canvas-sketch) - Framework for generative artwork in JavaScript. `★ 5.3k` `MIT` `2026-06`
- [vanilla-tilt.js](https://github.com/micku7zu/vanilla-tilt.js) - Smooth 3D tilt on hover. `★ 4.0k` `MIT` `2024-03`
- [Hydra](https://github.com/hydra-synth/hydra) - Live-coded video synth in the browser: oscillators, kaleidoscopes, modulation and feedback. `★ 2.7k` `AGPL-3.0 ⚠` `2026-04`
- [use-scramble](https://github.com/tol-is/use-scramble) - React hook for a clean scramble (decrypt) text effect. `★ 146` `MIT` `2026-03`
<!-- LIST:END -->

## How the list stays current

Everything between the list markers in this file is generated. The curated part lives in [`list.json`](./list.json): the repository, a display name, a section and a one-line note.

```sh
GITHUB_TOKEN=$(gh auth token) node scripts/build.mjs
```

The script needs Node 18 or newer and has no dependencies. For each entry it fetches the current stars, license and last push, sorts each section by stars, and moves anything archived or without a push in three months to Quiet classics. If development resumes, the next run moves it back.

## Contributing

Suggestions are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[MIT](./LICENSE)
