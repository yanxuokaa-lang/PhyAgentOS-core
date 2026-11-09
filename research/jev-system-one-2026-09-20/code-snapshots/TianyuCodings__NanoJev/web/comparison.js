'use strict';
const $=id=>document.getElementById(id);
const roles=['trained','jev','base'];
const names={trained:'NanoJev',jev:'Jev',base:'Untuned Qwen'};
const kinds={trained:'0.6B',jev:'API',base:'Untuned'};
const directions={north:'↑ North',east:'→ East',south:'↓ South',west:'← West'};
const state={data:null,policy:'greedy',caseIndex:0,stepIndex:0,timer:null};
const make=(tag,cls,text)=>{const e=document.createElement(tag);e.className=cls??'';if(text!==undefined)e.textContent=text;return e;};
function selectedCase(){return state.data?.cases[state.caseIndex];}
function models(){return state.data?.models.filter(m=>m.policy===state.policy)??[];}
function episode(model){return model.episodes.find(e=>e.id===selectedCase().id);}
function duration(){return Math.max(0,...models().map(m=>episode(m).steps.length));}
function stop(){clearInterval(state.timer);state.timer=null;$('play').textContent='Play';}
function grid(environment,trace){
 const e=make('div','grid');e.style.setProperty('--size',environment.size);
 const walls=new Set(environment.walls.map(c=>c.join(','))),visited=new Set(trace.map(s=>s.state.position.join(',')));
 for(let r=0;r<environment.size;r++)for(let c=0;c<environment.size;c++){
  const key=[r,c].join(','),isAgent=environment.position.join(',')===key,isGoal=environment.goal.join(',')===key;
  const item=make('div','cell'+(walls.has(key)?' wall':'')+(visited.has(key)?' trail':'')+(isGoal?' goal':'')+(isAgent?' agent':''));
  item.append(make('span','coordinate',`${r},${c}`));if(isAgent||isGoal)item.append(make('span','mark',isAgent?'●':'◎'));e.append(item);
 }return e;
}
function outcome(ep){return ep.success===true||ep.outcome==='goal'?'Goal reached':ep.outcome==='horizon_exhausted'?'Step limit reached':ep.outcome??'Replay complete';}
function panel(model){
 const ep=episode(model),index=Math.min(state.stepIndex,ep.steps.length),transition=ep.steps[index],finished=index>=ep.steps.length;
 const environment=transition?.state??ep.final_state??ep.steps.at(-1)?.next_state??ep.initial_state;
 const p=make('article',`panel ${model.role}`);p.dataset.role=model.role;
 const heading=make('div','panel-heading'),title=make('div');title.append(make('h2','system-name',names[model.role]),make('p','system-detail',model.display_detail??model.name));heading.append(title,make('span','kind',kinds[model.role]));p.append(heading);
 const meta=make('div','step-meta');meta.append(make('span',`status${finished?ep.success?' success':' failure':''}`,finished?outcome(ep):'In progress'),make('span','step-count',`${index} steps taken`));p.append(meta,grid(environment,ep.steps.slice(0,index)));
 const action=make('div','action-line');action.append(make('span','',finished?'Final outcome':'Next action'),make('strong','',finished?'—':directions[transition.action]??transition.action));p.append(action);
 const probabilities=make('div','probabilities');
 if(transition&&transition.probabilities&&Object.keys(transition.probabilities).length){
  const entries=Object.entries(transition.probabilities).sort((a,b)=>Object.keys(directions).indexOf(a[0])-Object.keys(directions).indexOf(b[0]));
  for(const [id,value] of entries){const item=make('div',`probability${id===transition.action?' selected':''}`);item.dataset.action=id;const line=make('div','row');line.append(make('span','',directions[id]??id),make('span','',`${(value*100).toFixed(1)}%`));const track=make('div','track'),fill=make('div','fill');fill.style.width=`${Math.max(0,Math.min(1,value))*100}%`;track.append(fill);item.append(line,track);probabilities.append(item);}
 }else probabilities.append(make('div',`final-message${finished?ep.success?' success':' failure':''}`,finished?ep.success?'✓ Goal reached':'× Step limit reached':'Action probabilities not recorded'));
 p.append(probabilities);
 let note=finished?`Full trajectory: ${ep.steps.length} steps · holding final state`:transition.forced?'Only legal action':state.policy==='sample'?'Action probabilities · sampled action highlighted':'Action probabilities · chosen action highlighted';
 if(transition?.probabilities){const total=Object.values(transition.probabilities).reduce((a,b)=>a+b,0);if(Math.abs(total-1)>1e-5)note+=` Recorded sum: ${total.toFixed(3)}.`;}
 p.append(make('p','prob-note',note));
 const provenance=make('p','summary-steps');provenance.append(make('span','',model.role==='jev'?'Jev API · typed action probabilities':model.role==='base'?'Original weights · A–D action probabilities':'0.6B · parallel decisions'));p.append(provenance);
 return p;
}
function render(){
 if(!state.data)return;const c=selectedCase(),max=duration();state.stepIndex=Math.max(0,Math.min(state.stepIndex,max));
 $('caseBadge').textContent=`${c.split.toUpperCase()} ${c.split_index} / 2`;$('mapLabel').textContent=`${c.initial_state.size}×${c.initial_state.size} grid · selected case ${state.caseIndex+1} / ${state.data.cases.length}`;
 $('controllerLabel').textContent=state.policy==='sample'?'Sample from each distribution · T=1':'Highest-probability action · greedy';$('globalStep').textContent=`Step ${state.stepIndex} / ${max}`;$('caseId').textContent=c.id;
 $('panels').replaceChildren(...roles.map(role=>panel(models().find(m=>m.role===role))));
 $('slider').max=String(max);$('slider').value=String(state.stepIndex);$('prev').disabled=state.stepIndex===0;$('next').disabled=state.stepIndex===max;
 window.nanojevComparison.snapshot={policy:state.policy,case_index:state.caseIndex,case_id:c.id,step_index:state.stepIndex,panels:models().map(m=>{const e=episode(m),i=Math.min(state.stepIndex,e.steps.length);return{role:m.role,step_index:i,finished:i===e.steps.length,environment:e.steps[i]?.state??e.final_state??e.steps.at(-1)?.next_state??e.initial_state,action:e.steps[i]?.action??null};})};
}
window.nanojevComparison={ready:false,setFrame(policy,caseIndex,stepIndex){stop();state.policy=policy;state.caseIndex=caseIndex;state.stepIndex=stepIndex;$('policySelect').value=policy;$('caseSelect').value=String(caseIndex);render();return this.snapshot;},duration(policy,caseIndex){const old=[state.policy,state.caseIndex];state.policy=policy;state.caseIndex=caseIndex;const n=duration();[state.policy,state.caseIndex]=old;return n;}};
$('policySelect').addEventListener('change',e=>{stop();state.policy=e.target.value;state.stepIndex=0;render();});$('caseSelect').addEventListener('change',e=>{stop();state.caseIndex=Number(e.target.value);state.stepIndex=0;render();});
$('prev').addEventListener('click',()=>{stop();state.stepIndex--;render();});$('next').addEventListener('click',()=>{stop();state.stepIndex++;render();});$('slider').addEventListener('input',e=>{stop();state.stepIndex=Number(e.target.value);render();});
$('play').addEventListener('click',()=>{if(state.timer)return stop();if(state.stepIndex===duration())state.stepIndex=0;$('play').textContent='Pause';render();state.timer=setInterval(()=>{state.stepIndex++;render();if(state.stepIndex===duration())stop();},500);});
(async()=>{try{const response=await fetch('./comparison_results.json',{cache:'no-store'});if(!response.ok)throw Error('Recorded showcase data unavailable');const data=await response.json();if(!Array.isArray(data.cases)||!Array.isArray(data.models)||!data.cases.length)throw Error('Invalid showcase schema');
 const policies=[...new Set(data.models.map(m=>m.policy))];for(const policy of policies){for(const role of roles){const matches=data.models.filter(m=>m.policy===policy&&m.role===role);if(matches.length!==1||data.cases.some(c=>!matches[0].episodes.some(e=>e.id===c.id)))throw Error('A system trajectory or selected map is missing');}}
 state.data=data;state.policy=policies.includes('greedy')?'greedy':policies[0];$('policySelect').replaceChildren(...policies.map(p=>{const e=make('option','',p==='sample'?'Probability sampling · T=1':'Highest probability · greedy');e.value=p;return e;}));$('caseSelect').replaceChildren(...data.cases.map((c,i)=>{const e=make('option','',`${c.split.toUpperCase()} ${c.split_index} · ${c.initial_state.size}×${c.initial_state.size}`);e.value=String(i);return e;}));for(const id of ['policySelect','caseSelect','play','slider'])$(id).disabled=false;render();window.nanojevComparison.ready=true;window.nanojevComparison.data=data;$('loadStatus').textContent='Recorded showcase loaded · synchronized by environment step';
 }catch(error){$('loadStatus').textContent=error.message+'. No recorded trajectories are available.';$('loadStatus').classList.add('error');window.nanojevComparison.error=error.message;}})();
