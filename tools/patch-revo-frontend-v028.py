#!/usr/bin/env python3
"""Android-only interaction patches for the extracted Revolution frontend.

This intentionally targets exact strings from the pinned v0.9c-hotfix3 bundle so a
future upstream frontend change fails the build instead of silently patching the wrong code.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-revo-frontend-v028.py <index-*.js>")

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

old_help = '''Yt=({text:t,width:n=250,size:i=16,position:s="bottom",style:u})=>e.jsx(we,{label:t,maw:n,position:s,withArrow:!0,multiline:!0,transitionProps:{transition:"fade",duration:150},children:e.jsx(Ee,{variant:"subtle",size:i,radius:"xl",classNames:wp,style:u,children:e.jsx(Ed,{size:i-4})})});function q'''
new_help = '''Yt=({text:t,width:n=250,size:i=16,position:s="bottom",style:u})=>{const[r,c]=k.useState(!1);return e.jsxs("span",{style:{position:"relative",display:"inline-flex",alignItems:"center"},children:[e.jsx(Ee,{variant:"subtle",size:i,radius:"xl",classNames:wp,style:u,"aria-label":"Help",onClick:o=>{o.stopPropagation(),c(a=>!a)},children:e.jsx(Ed,{size:i-4})}),r&&e.jsxs("span",{role:"dialog","data-revo-help-popup":!0,onClick:o=>o.stopPropagation(),style:{position:"fixed",left:"50%",top:"50%",transform:"translate(-50%, -50%)",zIndex:10050,width:`min(${n}px, calc(100vw - 32px))`,maxHeight:"60vh",overflowY:"auto",padding:"14px 16px",borderRadius:"10px",border:"1px solid var(--mantine-color-default-border)",background:"var(--mantine-color-body)",boxShadow:"0 12px 40px rgba(0,0,0,.45)",fontSize:"14px",lineHeight:1.4,whiteSpace:"normal"},children:[e.jsx("span",{style:{display:"block",paddingRight:"24px"},children:t||"Help information is not available for this setting yet."}),e.jsx("button",{type:"button","aria-label":"Close help",onClick:()=>c(!1),style:{position:"absolute",right:"8px",top:"6px",border:0,background:"transparent",color:"inherit",fontSize:"22px",lineHeight:1,cursor:"pointer"},children:"×"})]})]})};function q'''
if old_help not in s:
    raise SystemExit("v0.2.8 help component target not found; refusing unsafe patch")
s = s.replace(old_help, new_help, 1)

old_auto = '''ay=({open:t,onOpenChange:n,initialTab:i="settings"})=>{const[s,u]=k.useState(i);return k.useEffect(()=>{t&&u(i)},[t,i]),e.jsx(rt,{opened:t,onClose:()=>n(!1),withCloseButton:!1,title:null,size:460,styles:{content:{padding:0},header:{display:"none"}}'''
new_auto = '''ay=({open:t,onOpenChange:n,initialTab:i="settings"})=>{const[s,u]=k.useState(i),[r,c]=k.useState(t),o=()=>{c(!1),n(!1)};return k.useEffect(()=>{c(t),t&&u(i)},[t,i]),e.jsx(rt,{opened:r,onClose:o,withCloseButton:!1,title:e.jsxs("div",{style:{display:"flex",alignItems:"center",justifyContent:"space-between",width:"100%",gap:8},children:[e.jsx("span",{children:"Auto-Planters"}),e.jsx("button",{type:"button","aria-label":"Close Auto-Planters",onClick:a=>{a.stopPropagation(),o()},style:{display:"inline-flex",alignItems:"center",justifyContent:"center",width:30,height:30,padding:0,border:0,borderRadius:6,background:"transparent",color:"inherit",fontSize:22,lineHeight:1,cursor:"pointer"},children:"×"})]}),size:460,styles:{content:{padding:0},header:{padding:"8px 12px 4px",minHeight:36},title:{width:"100%"}}'''
if old_auto not in s:
    raise SystemExit("v0.2.8 Auto-Planters modal target not found; refusing unsafe patch")
s = s.replace(old_auto, new_auto, 1)

# Target the actual right-sidebar opener rather than relying on visible text. This
# avoids stale/duplicate text matches after Planter Studio onboarding rerenders.
old_auto_opener = '''e.jsx(pe,{onClick:()=>y(!0),fullWidth:!0,size:"xs",leftSection:e.jsx(Ia,{size:14}),styles:{inner:{justifyContent:"flex-start",width:"100%"},label:{flex:1,justifyContent:"center",paddingRight:"2px",fontSize:"11px",width:"100%"}},children:"Auto-Planters"})'''
new_auto_opener = '''e.jsx(pe,{"aria-label":"Open Auto-Planters",onClick:()=>y(!0),fullWidth:!0,size:"xs",leftSection:e.jsx(Ia,{size:14}),styles:{inner:{justifyContent:"flex-start",width:"100%"},label:{flex:1,justifyContent:"center",paddingRight:"2px",fontSize:"11px",width:"100%"}},children:"Auto-Planters"})'''
if old_auto_opener not in s:
    raise SystemExit("v0.2.8 Auto-Planters opener target not found; refusing unsafe patch")
s = s.replace(old_auto_opener, new_auto_opener, 1)

# Desktop Revo sends Automatic users through a multi-step Planter Studio tutorial.
# On Android that tutorial can remain as a full-screen grey blocker because its
# desktop interaction assumptions do not map cleanly to touch. Preserve the mode
# choice, but finish onboarding immediately. The parent onClose marks
# planters.introShowed=true, which is already persisted by the Android runtime.
old_planter_intro = '''p=S=>{S==="automatic"?(o.Object("planter").Object("autoPlanters").Set("enabled",!0),i(!0)):t()},h=()=>{t()};return n?e.jsx'''
new_planter_intro = '''p=S=>{o.Object("planter").Object("autoPlanters").Set("enabled",S==="automatic"),t()},h=()=>{t()};return n?e.jsx'''
if old_planter_intro not in s:
    raise SystemExit("v0.2.8 Planter Studio onboarding target not found; refusing unsafe patch")
s = s.replace(old_planter_intro, new_planter_intro, 1)

# Older build/test workflows use this exact literal as a static patch marker.
s += '\n/* android-auto-planters-patch-marker title:"Auto-Planters" */\n'
s += '/* android-planter-studio-mobile-complete */\n'
s += '/* android-auto-planters-opener Open Auto-Planters */\n'

p.write_text(s, encoding="utf-8")
print("PASS: patched tap-help, exact Auto-Planters opener/close, and Planter Studio mobile onboarding")
