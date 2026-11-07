const fs=require('fs'),vm=require('vm'),assert=require('assert');
const script=fs.readFileSync(process.argv[2],'utf8');
const plan=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
let loaded=0,starts=0,stop=0,ready=true;const elements={};
const el=id=>elements[id]||(elements[id]={value:id==='account'?'Default':'',disabled:true,checked:false,
 textContent:'',className:'',callbacks:{},
 addEventListener(name,fn){this.callbacks[name]=fn},
 fire(name){return this.callbacks[name]()}});
let onReady;const document={getElementById:el,addEventListener(_name,fn){onReady=fn}};
const AndroidRevo={accessibilityReady(){return ready},
 configureMacro(cfg){loaded++;assert(JSON.parse(cfg).enablePlannedExecution);return JSON.stringify({patternName:'e_lol',patternStepCount:18})},
 startMacroAndRoblox(){starts++;return true},
 getEngineState(){return JSON.stringify({running:starts>0})},
 stopAll(){stop++},pauseMacro(){},openAccessibilitySettings(){}};
const window={AndroidRevo};
vm.runInNewContext(script,{window,document,console,
 setInterval(){},fetch:async()=>({ok:true,text:async()=>JSON.stringify(plan)})});
onReady();assert(el('start').disabled);assert(window.RevoResearchUI.checkPlan(plan).executable);
const altered=JSON.parse(JSON.stringify(plan));altered.actions[0].direction='FORWARD';
assert(!window.RevoResearchUI.checkPlan(altered).executable);
(async()=>{
 await el('load-sample').fire('click');
 assert(el('start').disabled);
 assert(!el('authorize').checked);
 el('authorize').checked=true;el('authorize').fire('change');
 assert(!el('start').disabled);
 el('start').fire('click');assert.strictEqual(loaded,1);assert.strictEqual(starts,1);
 el('stop').fire('click');assert.strictEqual(stop,1);
 ready=false;el('refresh').fire('click');assert(el('start').disabled);
 ready=true;el('refresh').fire('click');
 el('plan-input').value=JSON.stringify({...plan,pattern:'other'});
 el('plan-input').fire('input');assert(!el('authorize').checked);assert(el('start').disabled);
 el('validate').fire('click');assert(el('start').disabled);
 console.log('PASS: research UI starts only after valid sample, consent, and accessibility');
})().catch(e=>{console.error(e);process.exitCode=1});
